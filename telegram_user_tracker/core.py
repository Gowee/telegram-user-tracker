import re

from telethon import TelegramClient, events
from telethon.tl.types import InputMediaEmpty

from .client import client
from . import contacts
from .storage import MessageStorage
from .utils import DummyFile

count = 0
storage = MessageStorage("me", "test")


@client.on(events.NewMessage(pattern="(?i).*Hello"))
async def handler(event):
    global count
    await event.reply("Hey!")
    count += 1
    await storage.store(("Count = " + str(count)).encode("utf-8"))


@client.on(events.NewMessage(pattern="(?i).*test"))
async def handler_test(event):
    # print(await contacts.get_blocked())
    async for contact in contacts.iter_blocked():
        print(contact)


@client.on(events.NewMessage(pattern="(?i).*block.*"))
async def handler_block(event):
    user = re.search(r"block (.+)", event.message.message).group(1)
    print(user)
    return await contacts.block(int(user))


@client.on(events.NewMessage(pattern="(?i).*unblock.*"))
async def handler_unblock(event):
    user = re.search(r"unblock (.+)", event.message.message).group(1)
    print(user)
    return await contacts.unblock(int(user))


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


# async def keep_tracking():
#     pass


# # async def get_previous()


# async def check_blocked():
#     pass
