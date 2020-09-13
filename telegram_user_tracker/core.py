import re
import json
import logging
from asyncio import sleep as aiosleep
from urllib.parse import urlparse

from telethon import TelegramClient, events

from .client import client
from . import contacts
from .storage import MessageStorage
from .utils import (
    DummyFile,
    serialize_vector,
    deserialize_vector,
    EMTPY_VECTOR,
    render_user,
    render_datetime,
)
from .config import CHECK_INTERVAL, REPORT_CHANNEL

logger = logging.getLogger(__name__)
blockedUsersStorage = MessageStorage("me", "blocked_users", default=EMTPY_VECTOR)
# runtimeConfigStorage = MessageStorage("me", "runtime_config")


@client.on(events.NewMessage(pattern="(?i).*Hello"))
async def handler(event):
    await event.reply("Hey!")


@client.on(events.NewMessage(pattern="(?i).*test"))
async def handler_test(event):
    logger.debug(event)


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
    await report(
        f"🆕 {target.id} {(render_user(target))} is under #tracking, as requested by {render_user(requester)}."
    )
    await contacts.block(target)
    # TODO: check return value for success


@client.on(events.NewMessage(pattern="(?i)[!/]ignore(?P<args>.*)"))
async def handler_ignore(event):
    requester = await client.get_entity(event.message.from_id)
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{event.message.from_id} request to ignore {target} which is invalid: {e}"
        )
        return
    await report(
        f"❌ {target.id} {(render_user(target))} is now #ignored, as requested by {render_user(requester)}."
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

                msg = await client.get_messages(chat, ids=int(msgid))
                target = msg.from_id
            else:
                # This works only for cases where the session has cached the entities of the target.
                # Ref: https://docs.telethon.dev/en/latest/concepts/entities.html
                target = int(args)  # if it is a id
        except ValueError:
            target = args
    return target


async def report(message: str, *args, **kwargs):
    """Send message to the `REPORT_CHANNEL`."""
    return await client.send_message(
        REPORT_CHANNEL,
        message,
        # parse_mode="markdown",
        *args,
        **kwargs,
    )


async def keep_tracking():
    await aiosleep(3)
    while True:
        logger.info("Tracker is checking")
        try:
            await check_and_report()
        except Exception:
            logger.warning(f"Error when check_and_report", exc_info=True)
        await aiosleep(CHECK_INTERVAL)


async def check_and_report():
    d = await blockedUsersStorage.load()
    # `deserialize_vector` may keepping waiting for reading stream if b is invalid, so there should
    # have been a default value i.e. `EMPTY_VECTOR` there.
    assert d
    previous_blocked = {user.id: user for user in deserialize_vector(d)}
    now_blocked = []
    async for user in contacts.iter_blocked():
        if user.id in previous_blocked:
            user_previous = previous_blocked[user.id]
            pr = render_user(user_previous)
            cr = render_user(user)
            if pr != cr:
                await report(
                    f"🔠 {user.id} {render_user(user_previous)} #changed (user)name:\n"
                    f"to ➡️ {render_user(user)}\n"
                    f"now is at {render_datetime()}"
                )
            if not user_previous.deleted and user.deleted:
                await report(
                    f"💥 {user.id} / {render_user(user_previous)} account #deleted\n"
                    f"blocked at {render_datetime(user.date_blocked)}\n"
                    f"now is at {render_datetime()}"
                )
            logger.debug(f"{user.id} has no significant status change")
        else:
            await report(
                f"♻️ {user.id} {render_user(user)} is #newly added to the blocklist:\n"
                f"now is at {render_datetime()}"
            )
            logger.debug(f"{user.id} is newly found")
            # TODO: avoid race condition
        now_blocked.append(user)
    if (serialized := serialize_vector(now_blocked)) != d:
        await blockedUsersStorage.store(serialized)
