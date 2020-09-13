"""Use Telegram messages as persistent storage"""
import logging
from base64 import b85encode, b85decode
import re

from telethon import TelegramClient
from telethon.tl.types import (
    InputMessagesFilterDocument,
    InputMessagesFilterEmpty,
    Message,
    MessageMediaDocument,
)
from telethon.hints import EntitiesLike

from .client import client
from .utils import b85size, DummyFile

logger = logging.getLogger(__name__)

# from

REGEX_MESSAGE_PAYLOAD = re.compile(r"::([\w!#$%&()*+-;<=>?@^_`{|}~]*)::")


class MessageStorage:
    key: str
    ident: str
    chat: EntitiesLike
    message: Message
    default: bytes

    def __init__(self, chat: EntitiesLike, key: str, default: bytes=b''):
        self.key = key
        self.ident = f"#message_storage_{key}"
        self.chat = chat
        self.message = None
        self.default = default

    def __repr__(self):
        return f"{self.__class__.__name__}(chat={self.chat}, key={self.key!r})"

    async def ensure_prepared(self):
        if not self.message:
            return await self.prepare()

    async def prepare(self):
        entries = await client.get_messages(
            self.chat,
            limit=2,
            search=self.ident,
            filter=None,  # (InputMessagesFilterDocument, InputMessagesFilterEmpty),
            from_user="me",
        )
        if entries:
            self.message = entries[0]
        else:
            logger.debug(f"Creating a new message for {self!r}")
            self.message = await client.send_message(
                self.chat, f"{self.ident} ```\n::{b85encode(self.default).decode('latin-1')}::\n```"
            )

    async def load(self) -> bytes:
        await self.ensure_prepared()
        assert self.message  # prepare should be done first
        if self.message.media and isinstance(self.message.media, MessageMediaDocument):
            d = await client.download_media(self.message, bytes)
        elif match := REGEX_MESSAGE_PAYLOAD.search(self.message.message):
            d = b85decode(match.group(1))
        else:
            raise Exception(
                f"The old message used for storage with key {self.key} is unrecognizable"
            )
        return d

    async def store(self, data: bytes):
        await self.ensure_prepared()
        assert self.message
        # assuming edit_message is faster than re-uploading documents,
        # and hence prefering to the former whenever possible

        # the maximum bytes length of message body seems to be 4906
        # hardcode a safe value to avoid reach the limit
        if b85size(data) > 3600:
            if self.message.media and isinstance(
                self.message.media, MessageMediaDocument
            ):
                logger.debug(f"editing media: {data[:10]}... for key {self.key}")
                self.message = await client.edit_message(
                    self.chat,
                    self.message,
                    text=self.ident,
                    file=DummyFile("data.bin", data),
                    force_document=True,
                )
            else:
                logger.debug(
                    f"replacing text with document: {data[:10]}... for key {self.key}"
                )
                await client.delete_messages(self.chat, self.message)
                self.message = await client.send_message(
                    self.chat, self.ident, file=DummyFile("data.bin", data)
                )
        else:
            if self.message.media and isinstance(
                self.message.media, MessageMediaDocument
            ):
                logger.debug(
                    f"replacing document with text: {data[:10]}... for key {self.key}"
                )
                await client.delete_messages(self.chat, self.message)
                self.message = await client.send_message(
                    self.chat,
                    f"{self.ident} ```\n::{b85encode(data).decode('latin-1')}::\n```",
                )
            else:
                logger.debug(f"editing message: {data[:10]}... for key {self.key}")
                self.message = await client.edit_message(
                    self.chat,
                    self.message,
                    text=f"{self.ident} ```\n::{b85encode(data).decode('latin-1')}::\n```",
                )
