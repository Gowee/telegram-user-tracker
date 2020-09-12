from typing import Union, Sequence, BinaryIO
from math import ceil
from io import BytesIO
import struct

from telethon.tl.tlobject import TLObject
from telethon.extensions import BinaryReader


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


def serialize_vetor(vector: Sequence[TLObject]) -> bytes:
    # Ref: telethon.extensions.BinaryReader.tgread_vector
    # b = BytesIO()
    # b.write()
    # struct.pack_into(b, vector,)
    s = struct.pack("<II", 0x1CB5C415, len(vector)) + b"".join(
        tlobject._bytes() for tlobject in vector
    )
    # print(s)
    return s

def deserialize_vetor(vector: bytes) -> Sequence[TLObject]:
    return BinaryReader(vector).tgread_vector()

# def serialize_vetor(vector: Iterable[TLObject], buffer: BinaryIO) -> bytes:
#     b = BytesIO()
#     b.write()
#     struct.pack_into(b, vector,)


class DummyFile(BytesIO):
    name: str

    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name
