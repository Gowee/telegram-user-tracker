import logging
import asyncio

from .config import LOG_LEVEL

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=LOG_LEVEL
)

from .core import client, keep_tracking

logger = logging.getLogger(__name__)

logger.info("Up and running...")


async def main():
    await client.connect()
    print(1)
    tracking_task = asyncio.create_task(keep_tracking())
    print(2)
    await client.run_until_disconnected()


with client:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    # client.loop.run_until_complete()
