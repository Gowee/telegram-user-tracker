from typing import Union, Sequence, BinaryIO
from math import ceil
from io import BytesIO
import struct
from datetime import datetime

from telethon.tl.tlobject import TLObject
from telethon.extensions import BinaryReader
from telethon.tl.types import User


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

EMTPY_VECTOR: bytes = struct.pack("<II", 0x1cb5c415, 0)

def serialize_vector(vector: Sequence[TLObject]) -> bytes:
    # Ref: telethon.extensions.BinaryReader.tgread_vector
    # b = BytesIO()
    # b.write()
    # struct.pack_into(b, vector,)
    s = struct.pack("<II", 0x1CB5C415, len(vector)) + b"".join(
        tlobject._bytes() for tlobject in vector
    )
    # print(s)
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
        [
            name_part
            for name_part in (user.first_name, user.last_name)
            if name_part is not None
        ]
    )
    if not name or name.isspace():
        name = str(user.id)
    r = render_mention(user.id, name)
    # print("!",  user.username)
    if user.username:
        r += f" (@{user.username})"
    # print([name_part for name_part in (user.first_name, user.last_name) if name_part is not None])
    return r


def render_datetime(time: Union[datetime, None] = None) -> str:
    from .config import TIME_ZONE  # FIX

    if time is None:
        time = datetime.now(TIME_ZONE)
    return str(time.astimezone(TIME_ZONE))


# def serialize_vetor(vector: Iterable[TLObject], buffer: BinaryIO) -> bytes:
#     b = BytesIO()
#     b.write()
#     struct.pack_into(b, vector,)


class DummyFile(BytesIO):
    name: str

    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name
