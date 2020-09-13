import logging
import asyncio

from .config import LOG_LEVEL

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=LOG_LEVEL
)

from .core import client, keep_tracking
from .utils import render_user

logger = logging.getLogger(__name__)

logger.info("Up and running...")


async def main():
    await client.connect()
    me = await client.get_me()
    logger.info(f"Current acccount: {render_user(me)}")
    _tracking_task = asyncio.create_task(keep_tracking())
    await client.run_until_disconnected()


with client:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    # client.loop.run_until_complete()
