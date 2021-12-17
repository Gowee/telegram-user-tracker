from typing import Sequence
import re
import json
import logging
from asyncio import sleep as aiosleep, Lock
from urllib.parse import urlparse
import functools

from telethon import TelegramClient, events
from telethon.tl.types import User, MessageMediaDocument

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
    get_sender_id,
)
from .config import CHECK_INTERVAL, REPORT_CHANNEL, ROOT_ADMIN
from .auth import get_admins, add_admin, remove_admin, clear_admins, for_admins_only

logger = logging.getLogger(__name__)
blockedUsersStorage = MessageStorage("me", "blocked_users", default=EMTPY_VECTOR)
# runtimeConfigStorage = MessageStorage("me", "runtime_config")


@client.on(events.NewMessage(pattern=r"(?i).*Hello[, !] ?tracker"))
@for_admins_only()
async def handler(event):
    await event.reply("Hey!")


@client.on(events.NewMessage(pattern=r"(?i).*test"))
@for_admins_only()
async def handler_test(event):
    logger.info(event)


@client.on(events.NewMessage(pattern=r"(?i)[!/]track(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_track(event):
    logger.debug(event)
    requester = await client.get_entity(get_sender_id(event.message))
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{get_sender_id(event.message)} request to track {target} which is invalid: {e}"
        )
        return
    await contacts.block(target)
    # TODO: check return value for success
    await check_and_report(users_ignored=(target.id,))
    await report(
        f"➕ #u_{target.id} {(render_user(target))} is under #tracking, as requested by {render_user(requester)}."
    )


@client.on(events.NewMessage(pattern=r"(?i)[!/]ignore(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_ignore(event):
    requester = await client.get_entity(get_sender_id(event.message))
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        logger.info(
            f"{get_sender_id(event.message)} request to ignore {target} which is invalid: {e}"
        )
        return
    await contacts.unblock(target)
    await check_and_report(users_ignored=(target.id,))
    await report(
        f"➖ #u_{target.id} {(render_user(target))} is now #ignored, as requested by {render_user(requester)}."
    )


@client.on(events.NewMessage(pattern=r"(?i)[!/]list[_\- ]tracked(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_list_tracked(event):
    requester = await client.get_entity(get_sender_id(event.message))
    d = await blockedUsersStorage.load()
    assert d
    blocked = deserialize_vector(d)
    msg = f"Current tracking list, as requested by {render_user(requester)} at {render_datetime()}:\n"
    msg += "\n".join(f"#u_{user.id} {render_user(user)}" for user in blocked)
    await report(msg)


@client.on(events.NewMessage(pattern="(?i)[!/]elevate(?P<args>.*)"))
@for_admins_only(root=True)
async def handler_elevate(event):
    requester = await client.get_entity(get_sender_id(event.message))
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
    requester = await client.get_entity(get_sender_id(event.message))
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
    requester = await client.get_entity(get_sender_id(event.message))
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
    requester = await client.get_entity(get_sender_id(event.message))
    await report(
        f"⚠️ All admins privileges are lifted as requested by {render_user(requester)}."
    )
    logger.info(f"{render_user(requester)} requests to lift all admins' privileges")


async def _extract_target_user_id(event) -> int:
    if reply_to := await event.message.get_reply_message():
        # Targeted at the sender of a replied-to messsage, with no extra args needed.
        target = get_sender_id(reply_to)
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
                    chat = int(chat)  # here chat is numeric id
                else:
                    # in a public group
                    chat, msgid = url[2].lstrip("/").split("/")
                    # here chat is the @username of a group

                msg = await client.get_messages(chat, ids=int(msgid))
                target = get_sender_id(msg)
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
            try:
                await client.send_message(
                    ROOT_ADMIN or "me", __import__("traceback").format_exc()
                )
            except:
                pass
            logger.warning(f"Error when check_and_report", exc_info=True)
        await aiosleep(CHECK_INTERVAL)


check_lock = Lock()
tracked_user_ids = set()


async def check_and_report(users_ignored: Sequence[int] = tuple()):
    # global check_lock
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
                        f"💥 #u_{user.id} {pr} account #deleted\n"
                        f"tracking since {render_datetime(user.date_blocked)}\n"
                        f"now is at {render_datetime()}"
                    )
                elif pr != cr:
                    # If the account is deleted, its (user)names get cleared, in which case there
                    # is no need to report the name change
                    await report(
                        f"🔠 #u_{user.id} {pr} #changed (user)name:\n"
                        f"to ➡️ {cr}\n"
                        f"now is at {render_datetime()}"
                    )
                logger.debug(f"{user.id} has no significant status change")
            elif user.id not in users_ignored:
                # TODO: when a account is deleted and recreated within one check interval, the
                # recreation message should be reported after the deletion message
                await report(
                    f"🆕 #u_{user.id} {render_user(user)} is #newly found:\n"
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
                await report(
                    f"❕ #u_{user.id} {render_user(user)} #joined {render_chat(chat)}\nnow is at {render_datetime()}"
                )


@client.on(events.NewMessage(pattern=r"(?i)[!/]inspect(?P<args>.*)"))
@for_admins_only(root=False)
async def handler_inspect(event):
    requester = await client.get_entity(get_sender_id(event.message))
    target = await _extract_target_user_id(event)
    try:
        target = await client.get_entity(target)
    except ValueError as e:
        # await event.reply(f"{target} is invalid")
        logger.info(
            f"{get_sender_id(event.message)} request to inspect {target} which is invalid: {e}"
        )
        return
    chats = await contacts.get_common_groups(target)
    message = f"Groups of #u_{target.id} {render_user(target)}, as requested by {render_user(requester)} at {render_datetime()}:\n"
    message += "\n".join(map(lambda chat: "• " + render_chat(chat), chats))
    logger.info(message)
    await report(message)
    # TODO: get first/last message link in each group
    # await event.reply(message) # <del># currently, only hello & inspect reply directly to the requester instead of the channel</del>


@client.on(events.NewMessage(pattern=r"(?i)[!/]export[-_ ]tracked"))
@for_admins_only(root=True)
async def handler_export_tracked(event):
    requester = await client.get_entity(get_sender_id(event.message))
    d = await blockedUsersStorage.load()
    assert d
    blocked = [user.to_dict() for user in deserialize_vector(d)]
    for user in blocked:
        # some fields cannot be accepted by BlockedUser constructor when deserializing
        del user["_"]  # type marker, i.e. `User`
        # TODO: the ser/de logic for BlockedUser is too complex. How about just using a plain json
        #       with a few specific fields instead?
        for k, v in user.items():
            if "restricted" in user:
                user["restricted"] = None
            if not isinstance(v, (str, int, bool, type(None), type(Ellipsis))):
                user[k] = None
    await event.reply(
        "",
        file=DummyFile(
            "tracked.json",
            json.dumps(
                blocked,
                indent=2,
                ensure_ascii=False,
                default=lambda _: None,  # filter out non-JSON-serializable types, such as bytes
            ).encode("utf-8"),
        ),
    )


@client.on(events.NewMessage(pattern=r"(?i)[!/]import[-_ ]tracked"))
@for_admins_only(root=True)
async def handler_import_tracked(event):
    # requester = await client.get_entity(get_sender_id(event.message))
    try:
        message = event.message
        if not message.media and (reply_to := await event.message.get_reply_message()):
            message = reply_to
        if message.media and isinstance(message.media, MessageMediaDocument):
            d = await client.download_media(message, bytes)
            imported = [
                contacts.BlockedUser(**user) for user in json.loads(d.decode("utf-8"))
            ]
            serialized = serialize_vector(imported)
            await blockedUsersStorage.init()
            await blockedUsersStorage.store(serialized)
            await event.reply(f"Overwritten with {len(imported)} entries.")
            await check_and_report()  # TODO: use a channel to trigger check
        else:
            await event.reply(f"No data file specified")
    except Exception:
        await event.reply(__import__("traceback").format_exc())
        logger.exception(f"Error when importing")


# TODO: abstract blocked users manager like .contacts or .auth so that to avoid manually managing
#       tracked_user_ids

# TODO: a standalone tool for data migrations instead of import/export commands?
