from typing import AsyncGenerator
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import User
from telethon.tl.types import contacts as types
from telethon.tl.functions import contacts as requests
from telethon.hints import EntitiesLike
from telethon.extensions import BinaryReader

# from

from .client import client
from .utils import struct


class BlockedUser(User):
    # WARNING: The CONSTRUCTOR_ID is the same as the super() while the serde binary format is not.
    #          But as it is not listed in telethon.tl.allobjects.tlobjects, there won't be problems
    #          unless it is unexpectedly serde elsewhere.
    date_blocked: datetime

    def __init__(self, date_blocked=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_blocked = date_blocked

    def to_dict(self):
        # for debugging purpose
        d = super().to_dict()
        d["date_blocked"] = self.date_blocked
        return d

    def _bytes(self):
        # struct.pack("<I", 0xF0F0F0F0) +
        return super()._bytes() + struct.pack("<L", int(self.date_blocked.timestamp()))

    @staticmethod
    def from_reader(self, reader):
        user = super().from_reader(reader)
        user.date_blocked = reader.read_long()
        user.__class__ = BlockedUser
        return user

async def get_blocked(offset: int = 0, limit: int = 100) -> types.Blocked:
    return await client(requests.GetBlockedRequest(offset, limit))


async def iter_blocked(offset=0, _chunk_size=100) -> AsyncGenerator[BlockedUser, None]:
    while True:
        d = await get_blocked(offset, _chunk_size)
        dates = {blocked.user_id: blocked.date for blocked in d.blocked}
        # users = {user.id: user for user in d.users}
        for user in d.users:
            user.date_blocked = dates[user.id]
            user.__class__ = BlockedUser
            yield user
        if (
            isinstance(d, types.Blocked) and not isinstance(d, types.BlockedSlice)
        ) or d.count < _chunk_size:
            break
        offset += d.count


async def block(user: EntitiesLike) -> bool:
    return await client(requests.BlockRequest(user))


async def unblock(user: EntitiesLike) -> bool:
    return await client(requests.UnblockRequest(user))
