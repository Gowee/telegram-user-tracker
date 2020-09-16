from typing import Sequence
import re
import json
import logging
from asyncio import sleep as aiosleep, Lock
from urllib.parse import urlparse
import functools

from telethon import TelegramClient, events
from telethon.tl.types import User

from .client import client
from . import contacts
from .storage import MessageStorage
from .utils import (
    DummyFile,
    serialize_vector,
    deserialize_vector,
    EMTPY_VECTOR,
    render_user,
    render_chat,
    render_datetime,
)
from .config import CHECK_INTERVAL, REPORT_CHANNEL, ROOT_ADMIN
from .auth import get_admins, add_admin, remove_admin, clear_admins, for_admins_only

logger = logging.getLogger(__name__)
blockedUsersStorage = MessageStorage("me", "blocked_users", default=EMTPY_VECTOR)
# runtimeConfigStorage = MessageStorage("me", "runtime_config")


@client.on(events.NewMessage(pattern="(?i).*Hello"))
async def handler(event):
    await event.reply("Hey!")


@client.on(events.NewMessage(pattern="(?i).*test"))
async def handler_test(event):
    logger.info(event)


@client.on(events.NewMessage(pattern=r"(?i)[!/]track(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_track(event):
    logger.debug(event)
    requester = await client.get_entity(event.message.from_id)
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{event.message.from_id} request to track {target} which is invalid: {e}"
        )
        return
    await contacts.block(target)
    # TODO: check return value for success
    await check_and_report(users_ignored=(target.id,))
    await report(
        f"➕ #u{target.id} {(render_user(target))} is under #tracking, as requested by {render_user(requester)}."
    )


@client.on(events.NewMessage(pattern="(?i)[!/]ignore(?P<args>.*)"))
@for_admins_only(root=False)
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
    await contacts.unblock(target)
    await check_and_report(users_ignored=(target.id,))
    await report(
        f"➖ #u{target.id} {(render_user(target))} is now #ignored, as requested by {render_user(requester)}."
    )


@client.on(events.NewMessage(pattern=r"(?i)[!/]list[_\- ]tracked(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_list_tracked(event):
    requester = await client.get_entity(event.message.from_id)
    d = await blockedUsersStorage.load()
    assert d
    blocked = deserialize_vector(d)
    msg = f"Currently tracking list, as requested by {render_user(requester)} at {render_datetime()}:\n"
    msg += "\n".join(f"#u{user.id} {render_user(user)}" for user in blocked)
    await report(msg)


@client.on(events.NewMessage(pattern="(?i)[!/]elevate(?P<args>.*)"))
@for_admins_only(root=True)
async def handler_elevate(event):
    requester = await client.get_entity(event.message.from_id)
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{render_user(requester)} requests to elevate {target} which is invalid: {e}"
        )
        return
    if await add_admin(target.id):
        await report(
            f"⚙️ {(render_user(target))} has been elevated into admin, as requested by {render_user(requester)}."
        )
    else:
        logging.info(
            f"{render_user(requester)} requests to elevate {render_user(target)} into admin, but it fails"
        )


@client.on(events.NewMessage(pattern="(?i)[!/]lift(?P<args>.*)"))
@for_admins_only(root=True)
async def handler_lift(event):
    requester = await client.get_entity(event.message.from_id)
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{render_user(requester)} requests to lift admin privileges of {target} which is invalid: {e}"
        )
        return
    if await remove_admin(target.id):
        await report(
            f"⚙️ {(render_user(target))} 's admin privileges has been lifted, "
            f"as requested by {render_user(requester)}."
        )
    else:
        logging.info(
            f"{render_user(requester)} requests to lift admin privileges of {render_user(target)} to admin, but it fails"
        )


@client.on(events.NewMessage(pattern=r"(?i)[!/]list[_\- ]admins(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_list_admins(event):
    requester = await client.get_entity(event.message.from_id)
    admins = []
    for user_id in await get_admins(refresh=True):
        admins.append(await client.get_entity(user_id))
    msg = f"Admins list, as requested by {render_user(requester)}:\n"
    msg += "\n".join(f"{render_user(user_id)}" for user_id in admins)
    #     msg += "\n".join(f"{render_user(await client.get_entity(user_id))}" for user_id in admins)
    # TypeError: can only join an iterable ?
    await report(msg)


@client.on(events.NewMessage(pattern=r"(?i)[!/]clear[\-_ ]admins(?P<args>.*)"))
@for_admins_only(root=True)
async def handler_clear_admins(event):
    await clear_admins()
    requester = await client.get_entity(event.message.from_id)
    await report(
        f"⚠️ All admins privileges are lifted as requested by {render_user(requester)}."
    )
    logger.info(f"{render_user(requester)} requests to list all admins' privileges")


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


check_lock = Lock()
tracked_user_ids = {}

async def check_and_report(users_ignored: Sequence[int] = tuple()):
    #global check_lock
    global tracked_user_ids
    async with check_lock:
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
                if not user_previous.deleted and user.deleted:
                    await report(
                        f"💥 #u{user.id} / {cr} account #deleted\n"
                        f"blocked at {render_datetime(user.date_blocked)}\n"
                        f"now is at {render_datetime()}"
                    )
                elif pr != cr:
                    # If the account is deleted, its (user)names get cleared, in which case there
                    # is no need to report the name change
                    await report(
                        f"🔠 #u{user.id} {pr} #changed (user)name:\n"
                        f"to ➡️ {cr}\n"
                        f"now is at {render_datetime()}"
                    )
                logger.debug(f"{user.id} has no significant status change")
            elif user.id not in users_ignored:
                # TODO: when a account is deleted and recreated within one check interval, the
                # recreation message should be reported after the deletion message
                await report(
                    f"🆕 #u{user.id} {render_user(user)} is #newly added to the blocklist:\n"
                    f"now is at {render_datetime()}"
                )
                logger.debug(f"{user.id} is newly found")
                # TODO: avoid race condition
            now_blocked.append(user)
        if (serialized := serialize_vector(now_blocked)) != d:
            await blockedUsersStorage.store(serialized)
        tracked_user_ids = {user.id for user in now_blocked}

@client.on(events.ChatAction(func=lambda event: event.user_joined or event.user_added))
async def handler_user_join(event):
    # TODO: there is possibility that some of joining messages are discarded
    async with check_lock:
        for user in await event.get_users():
            if user.id in tracked_user_ids:
                chat = await event.get_chat()
                await report(f"❕ #u{user.id} {render_user(user)} joined {render_chat(chat)}\nnow is at {render_datetime()}")

# TODO: abstract blocked users manager like .contacts or .auth so that to avoid manually managing
#       tracked_user_ids
