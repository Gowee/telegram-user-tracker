import re
import json
import logging
from asyncio import sleep as aiosleep
from urllib.parse import urlparse

from telethon import TelegramClient, events

# from telethon.tl.types import InputMediaEmpty

from .client import client
from . import contacts
from .storage import MessageStorage
from .utils import DummyFile, serialize_vector, deserialize_vector, render_user
from .config import CHECK_INTERVAL, REPORT_CHANNEL

logger = logging.getLogger(__name__)
blockedUsersStorage = MessageStorage("me", "blocked_users")
# runtimeConfigStorage = MessageStorage("me", "runtime_config")


# @client.on(events.NewMessage(pattern="(?i).*Hello"))
# async def handler(event):
#     global count
#     await event.reply("Hey!")
#     # count += 1
#     await blockedUsersStorage.store(("Count = " + str(count)).encode("utf-8"))


@client.on(events.NewMessage(pattern="(?i).*test"))
async def handler_test(event):
    # print(await contacts.get_blocked())
    # blocked = []
    # async for contact in contacts.iter_blocked():
    #     blocked.append(contact)
    # print(blocked)
    # serde = deserialize_vector(serialize_vector(blocked))
    # print(serde)
    print(event)
    print(event.message)


@client.on(events.NewMessage(pattern=r"(?i)[!/]track(?P<args>.*)"))
async def handler_track(event):
    print(event)
    requester = await client.get_entity(event.message.from_id)
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{event.message.from_id} request to track {target} which is invalid: {e}"
        )
        return
    # print(repr(target))
    await client.send_message(
        REPORT_CHANNEL,
        f"{(render_user(target))} / ID: {target.id} is under tracking, as requested by {render_user(requester)}.",
        parse_mode="markdown",
    )
    await contacts.block(target)
    # TODO: check return value for success


@client.on(events.NewMessage(pattern="(?i)[!/]ignore(?P<args>.*)"))
async def handler_ignore(event):
    # user = re.search(r"unblock (.+)", event.message.message).group(1)
    requester = await client.get_entity(event.message.from_id)
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{event.message.from_id} request to ignore {target} which is invalid: {e}"
        )
        return
    await client.send_message(  
        REPORT_CHANNEL,
        f"{(render_user(target))} / ID: {target.id} is now ignored, as requested by {render_user(requester)}.",
        parse_mode="markdown",
    )
    await contacts.unblock(target)


async def _extract_target_user_id(event) -> int:
    if reply_to := await event.message.get_reply_message():
        # Targeted at the sender of a replied-to messsage, with no extra args needed.
        target = reply_to.from_id
    else:
        # Or the target can be extracted from the args.
        args = event.pattern_match.group("args").strip()

        try:
            if (url := urlparse(args))[1].lower() == "t.me":
                # Hence mtproto does not allow locating a User by their ID without entities obtained in
                # advance, here accepting a message URL linked to a message the target sent.
                if url[2].startswith("/c/"):
                    # link to a message in a private chat
                    _, chat, msgid = url[2].lstrip("/").split("/")
                else:
                    # in a public group
                    chat, msgid = url[2].lstrip("/").split("/")

                print(url)
                msg = await client.get_messages(chat, ids=int(msgid))
                target = msg.from_id
            else:
                # This works only for cases where the session has cached the entities of the target.
                # Ref: https://docs.telethon.dev/en/latest/concepts/entities.html
                target = int(args)  # if it is a id
        except ValueError as e:
            target = args
    return target

# fff = None


# @client.on(events.NewMessage(pattern="(?i).*ta"))
# async def handler_ta(event):
#     # print(await contacts.get_blocked())
#     # print(await contacts.get_blocked(0, 5))
#     # print(await contacts.get_blocked(5, 100))
#     global fff
#     fff = await client.send_message(126777601, file=DummyFile("test.txt", b"testttt"))


# @client.on(events.NewMessage(pattern="(?i).*tb"))
# async def handler_tb(event):
#     # print(await contacts.get_blocked())
#     # print(await contacts.get_blocked(0, 5))
#     # print(await contacts.get_blocked(5, 100))
#     await client.delete_messages(126777601, fff)
#     print(fff.media.ttl_seconds)


# @client.on(events.NewMessage(pattern="(?i).*tc"))
# async def handler_tc(event):
#     # print(await contacts.get_blocked())
#     # print(await contacts.get_blocked(0, 5))
#     # print(await contacts.get_blocked(5, 100))
#     print(await client.download_media(fff, file=bytes))


async def keep_tracking():
    while True:
        logger.info("Tracker is checking")
        await check_and_report()
        await aiosleep(CHECK_INTERVAL)


# # async def get_previous()


async def check_and_report():
    d = await blockedUsersStorage.load()
    previous_blocked = {user.id: user for user in deserialize_vector(d)}

    #  = {}  # set(json.loads(await storage.load()))
    now_blocked = []
    # newly_blocked = []
    async for user in contacts.iter_blocked():
        now_blocked.append(user)
        if user in previous_blocked:
            pass
        else:
            pass
            # newly_blocked.append(user)

    # Update
