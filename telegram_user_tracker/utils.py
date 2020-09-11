from typing import Union
from math import ceil
from io import BytesIO


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


class DummyFile(BytesIO):
    name: str

    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name
