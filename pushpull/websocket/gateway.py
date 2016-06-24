"""
Pushpull websocket server
"""
import logging
import asyncio
import random

import aiohttp
import aiohttp.web

from ..amqp.gateway import Exchanger


logger = logging.getLogger(__name__)


async def websocket_rabbitmq_gateway(request):
    # TODO: AUTHENTICATION
    name = request.GET.get('name')
    if not name:
        return aiohttp.web.Response(body=b'name is required', status=400)
    ws = aiohttp.web.WebSocketResponse()
    logger.debug('websocket connection open')
    try:
        await ws.prepare(request)
        # TODO: get client_id from request
        async with Exchanger(name, Exchanger.ROLE_WS, client_id=random.randint(1, 100)) as (amqp_sender, amqp_receiver):
            send_coro = send_from_amqp_to_websocket(amqp_receiver, ws)
            receive_coro = send_from_websocket_to_amqp(ws, amqp_sender)
            await asyncio.gather(receive_coro, send_coro)
    except Exception as exc:
        logger.exception('exception while handling request')
    finally:
        logger.debug('websocket connection closing')
        await ws.close()
        return ws


async def send_from_websocket_to_amqp(ws, sender):
    async for msg in ws:
        if msg.tp == aiohttp.MsgType.text:
            logger.debug('got data: %s', msg.data)
            await sender.send(msg.data)
        elif msg.tp == aiohttp.MsgType.error:
            logger.error('ws connection closed with exception %s', ws.exception())
            return


async def send_from_amqp_to_websocket(receiver, ws):
    async for data in receiver:
        ws.send_str(data)
        # await ws._writer.writer.drain()


async def echo_websocket(ws):
    """For testing only """
    async for msg in ws:
        if msg.tp == aiohttp.MsgType.text:
            logger.debug('echoing data: %s', msg.data)
            ws.send_str(msg.data)
        elif msg.tp == aiohttp.MsgType.error:
            logger.error('ws connection closed with exception %s', ws.exception())
            return
