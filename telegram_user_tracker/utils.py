from typing import Union, Sequence, BinaryIO
from math import ceil
from io import BytesIO
import struct
from datetime import datetime

from telethon.tl.tlobject import TLObject
from telethon.extensions import BinaryReader
from telethon.tl.types import User, Channel, Chat, Message, PeerUser


def read_file(file_path: str, strip=True, raise_on_error=False) -> Union[str, None]:
    try:
        with open(file_path, "r") as f:
            c = f.read()
            if strip:
                c = c.strip()
            return c
    except FileNotFoundError as e:
        if raise_on_error:
            raise e
        else:
            return None


def b85size(data: bytes) -> int:
    return ceil(len(data) / 4) * 5


EMTPY_VECTOR: bytes = struct.pack("<II", 0x1CB5C415, 0)


def serialize_vector(vector: Sequence[TLObject]) -> bytes:
    # Ref: telethon.extensions.BinaryReader.tgread_vector
    # TODO: how to use `struct.pack_into` to take a writable buffer as the output?
    s = struct.pack("<II", 0x1CB5C415, len(vector)) + b"".join(
        tlobject._bytes() for tlobject in vector
    )
    return s


def deserialize_vector(vector: bytes) -> Sequence[TLObject]:
    return BinaryReader(vector).tgread_vector()


def _render_mention_html(id, text):
    return f'<a href="tg://user?id={id}">{text}</a>'


def _render_mention_markdown(id, text):
    return f"[{text}](tg://user?id={id})"


def render_user(user: User, html_instead_of_markdown: bool = False) -> str:
    if html_instead_of_markdown:
        render_mention = _render_mention_html
    else:
        render_mention = _render_mention_markdown
    name = " ".join(
        name_part
        for name_part in (user.first_name, user.last_name)
        if name_part is not None
    )
    if (
        not name
        or name.isspace()
        or not any(map(lambda char: char.isprintable(), name))
    ):  # e.g. b'\xe2\x81\xa5'
        name = str(user.id)
    r = render_mention(user.id, name)
    if user.username:
        r += f" (@{user.username})"
    return r


def render_chat(chat: Union[Chat, Channel, User]) -> str:
    if isinstance(chat, Chat):
        return f"{chat.title} ({chat.id})"
    elif isinstance(chat, Channel):
        return f"{chat.title} ({('@' + chat.username) or chat.id})"
    elif isinstance(chat, User):
        return render_user(chat)
    else:
        raise ValueError("chat is not of type `User`, `Channel` or `Chat`")


def render_datetime(time: Union[datetime, None] = None) -> str:
    from .config import TIME_ZONE  # FIX

    if time is None:
        time = datetime.now(TIME_ZONE)
    return str(time.astimezone(TIME_ZONE))


class DummyFile(BytesIO):
    name: str

    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name


def get_sender_id(message: Message) -> int:
    """Get `sender_id` of a `Message`"""
    sender_id = None
    if message.from_id is None:
        # in group chat
        # newer version of MTProto API has no from_id for message in group
        if isinstance(message.peer_id, PeerUser):
            sender_id = message.peer_id.user_id
    else:
        # private chat
        sender_id = message.from_id
    return sender_id
