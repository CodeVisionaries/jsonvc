from abc import ABC, abstractmethod
from . import storage_utils as jsu
from pathlib import Path


class JsonStorageProvider(ABC):

    @abstractmethod
    def load(self, json_hash: str) -> dict:
        """Retrieve JSON object using JSON hash""" 
        pass

    @abstractmethod
    def store(self, json_dict: dict) -> str:
        """Store JSON object and return JSON hash"""
        pass

    @abstractmethod
    def exists(self, json_hash: str) -> bool:
        """Check if JSON object associated with JSON hash exists"""
        pass


class JsonObjectIndex(ABC):

    @abstractmethod
    def index(self) -> list[str]:
        """Return set of JSON hashes"""
        pass

    @abstractmethod
    def size(self, json_hash: str) -> int:
        """Return size of JSON object associated with JSON hash"""
        pass


class LocalJsonStorageProvider(JsonStorageProvider, JsonObjectIndex):

    def __init__(self, storage_dir: Path):
        self._storage_dir = Path(storage_dir)

    def load(self, json_hash: str) -> dict:
        return jsu.load_json_object(json_hash, self._storage_dir)

    def store(self, json_dict: dict) -> str:
        return jsu.store_json_object(json_dict, self._storage_dir)

    def exists(self, json_hash: str) -> bool:
        return jsu.is_json_object_stored(json_hash, self._storage_dir)

    def index(self):
        itera = self._storage_dir.iterdir()
        files = [f for f in itera if jsu.is_filename_wellformed(f)]
        return list(f.stem for f in files)

    def size(self, json_hash: str) -> int:
        fp = jsu.construct_filepath(json_hash, self._storage_dir)
        return fp.stat().st_size
