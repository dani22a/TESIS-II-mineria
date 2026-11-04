import abc
from pathlib import Path

from .config import settings


class Storage(abc.ABC):
    """Private object storage. A MinIO/S3 implementation can replace LocalStorage."""

    @abc.abstractmethod
    def put(self, key: str, data: bytes) -> None: ...

    @abc.abstractmethod
    def get(self, key: str) -> bytes: ...


class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


def get_storage() -> Storage:
    return LocalStorage(settings.storage_dir)
