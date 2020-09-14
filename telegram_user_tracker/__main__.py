import logging
import asyncio

from .config import LOG_LEVEL, REPORT_CHANNEL, ROOT_ADMIN
from .auth import get_me

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=LOG_LEVEL
)

from .core import client, keep_tracking
from .utils import render_user

logger = logging.getLogger(__name__)

logger.info("Up and running...")


async def main():
    await client.connect()
    me = await get_me()
    logger.info(f"Current account: {render_user(me)}")
    logger.info(
        f"Report channel id: {REPORT_CHANNEL}, additional root admins: {ROOT_ADMIN}"
    )
    _dialogs = await client.get_dialogs()
    logger.debug(f"dialogs: {_dialogs}")
    try:
        _report_channel_participants = await client.get_participants(REPORT_CHANNEL)
        logger.debug(
            f"participants of the report channel: {_report_channel_participants}"
        )
    except ValueError:
        pass
    _tracking_task = asyncio.create_task(keep_tracking())
    await client.run_until_disconnected()


with client:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
