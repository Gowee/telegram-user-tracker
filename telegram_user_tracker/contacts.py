from typing import AsyncGenerator
from datetime import datetime

import telethon
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
    """A wrapper around `telethon.tl.types.User` with a extra field of the datetime that the user
    gets blocked"""

    # WARNING: The CONSTRUCTOR_ID is the same as the super() while the serde binary format is not.
    #          But as it is not listed in telethon.tl.allobjects.tlobjects, there won't be problems
    #          unless it is unexpectedly serde elsewhere.
    CONSTRUCTOR_ID = 0xF0F0F0F0
    SUBCLASS_OF_ID = User.CONSTRUCTOR_ID

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
        return (
            struct.pack("<I", 0xF0F0F0F0)
            + super()._bytes()
            + struct.pack("<Q", int(self.date_blocked.timestamp()))
        )

    @classmethod
    def from_reader(cls, reader):
        assert reader.read_int(signed=False) == cls.SUBCLASS_OF_ID
        user = super().from_reader(reader)
        user.date_blocked = reader.read_long(signed=False)
        user.__class__ = BlockedUser
        print(user)
        return user


telethon.tl.alltlobjects.tlobjects[BlockedUser.CONSTRUCTOR_ID] = BlockedUser


async def get_blocked(offset: int = 0, limit: int = 100) -> types.Blocked:
    return await client(requests.GetBlockedRequest(offset, limit))


async def iter_blocked(offset=0, _chunk_size=100) -> AsyncGenerator[BlockedUser, None]:
    while True:
        d = await get_blocked(offset, _chunk_size)
        dates = {blocked.user_id: blocked.date for blocked in d.blocked}
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
