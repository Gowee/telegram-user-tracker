from typing import Set
import json
import functools
import logging

from .config import ROOT_ADMIN
from .client import client
from .storage import MessageStorage
from .utils import get_sender_id


logger = logging.getLogger(__name__)

me = None


async def get_me():
    global me
    if me is None:
        me = await client.get_me()
    return me


adminsStorage = MessageStorage("me", "admins", default=b"[]")
admins = set()


async def get_admins(refresh=True) -> Set[int]:
    global admins
    if admins is None or refresh is True:
        d = await adminsStorage.load()
        admins = set(json.loads(d))
        if ROOT_ADMIN is not None:
            admins.add(ROOT_ADMIN)
        admins.add((await get_me()).id)
    return admins


async def add_admin(user_id: int) -> bool:
    global admins
    await get_admins()
    if user_id in admins:
        return False
    admins.add(user_id)
    await adminsStorage.store(json.dumps(list(admins)).encode("utf-8"))
    logger.info(f"New admin elevated: {user_id}")
    return True


async def remove_admin(user_id: int) -> bool:
    global admins
    await get_admins()
    if user_id not in admins or user_id in (ROOT_ADMIN, (await get_me()).id):
        return False
    admins.remove(user_id)
    await adminsStorage.store(json.dumps(list(admins)).encode("utf-8"))
    logger.info(f"Admin privileges lifted: {user_id}")
    return True


async def clear_admins():
    global admins
    await adminsStorage.reset()


def for_admins_only(root=False):
    # TODO: typing?
    def wrapper(command_handler):
        @functools.wraps(command_handler)
        async def wrapped(event):
            sender_id = get_sender_id(event.message)
            if root:
                admins = (ROOT_ADMIN, (await get_me()).id)
                # print(admins, sender_id)
                if not sender_id or sender_id not in admins:
                    return
            else:
                admins = await get_admins()
                if (
                    not sender_id
                    or sender_id not in admins
                    or sender_id
                    not in await get_admins(refresh=True)  # to avoid stale result
                ):
                    return
            return await command_handler(event)

        return wrapped

    return wrapper
