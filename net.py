import aiohttp
import asyncio
import time
import os
import random
import logging
import ssl

SESSION = None
VALID_HOSTS = ["www.cloudflare.com", "www.google.com", "www.microsoft.com"]

async def get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        connector = aiohttp.TCPConnector(
            limit=300,
            ttl_dns_cache=600,
            ssl=False
        )
        SESSION = aiohttp.ClientSession(connector=connector)
    return SESSION

async def close_session():
    global SESSION
    if SESSION and not SESSION.closed:
        await SESSION.close()
    SESSION = None

async def tcp_check(ip, timeout=0.8):
    start = time.perf_counter()
    ports = (443, 80)

    for port in ports:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True, (time.perf_counter() - start) * 1000
        except Exception:
            continue

    return False, 9999

async def tls_handshake(ip, timeout=1.5):
    start = time.perf_counter()

    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    sslctx.check_hostname = False
    sslctx.verify_mode = ssl.CERT_NONE

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 443, ssl=sslctx),
            timeout=timeout
        )

        writer.close()
        await writer.wait_closed()

        return True, (time.perf_counter() - start) * 1000

    except:
        return False, 9999

async def https_check(ip, total_timeout, tls_timeout):
    session = await get_session()
    start = time.perf_counter()
    host = random.choice(VALID_HOSTS)

    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    sslctx.check_hostname = False
    sslctx.verify_mode = ssl.CERT_NONE

    try:
        async with session.get(
            f"https://{ip}",
            timeout=aiohttp.ClientTimeout(total=total_timeout),
            headers={
                "Host": host,
                "User-Agent": "Mozilla/5.0"
            },
            allow_redirects=False,
            ssl=sslctx
        ) as r:
            await asyncio.wait_for(
                r.content.read(128),
                timeout=tls_timeout
            )
            return r.status < 400, (time.perf_counter() - start) * 1000
    except Exception as e:
        logging.debug(f"HTTPS check failed for {ip}: {e}")
        return False, 9999
