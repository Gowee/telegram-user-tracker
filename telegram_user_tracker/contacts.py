from typing import AsyncGenerator
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import User
from telethon.tl.types import contacts as types
from telethon.tl.functions import contacts as requests
from telethon.hints import EntitiesLike

from .client import client


class BlockedUser(User):
    date_blocked: datetime

    def __init__(self, date_blocked, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_blocked = date_blocked

    def to_dict(self):
        # for debugging purpose
        d = super().to_dict()
        d["date_blocked"] = self.date_blocked
        return d


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


async def block(user: EntitiesLike):
    return await client(requests.BlockRequest(user))


async def unblock(user: EntitiesLike):
    return await client(requests.UnblockRequest(user))
