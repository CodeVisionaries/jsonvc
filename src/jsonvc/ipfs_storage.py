from abc import ABC, abstractmethod
from . import ipfs_storage_utils as ipfs_jsu
from .storage import (
    JsonStorageProvider,
    JsonObjectIndex,
)
from pathlib import Path
from typing import Optional


class IpfsJsonStorageProvider(JsonStorageProvider):

    def __init__(self, cache_dir: Path, gateway_url: str, rpc_api_url: str, rpc_api_url_upload: Optional[str]=None):
        self._cache_dir = Path(cache_dir)
        self._gateway_url = gateway_url
        self._rpc_api_url = rpc_api_url
        self._rpc_api_url_upload = (
            rpc_api_url if rpc_api_url_upload is None else rpc_api_url_upload
        )
        self._cache_dir = Path(cache_dir)

    def load(self, json_hash: str) -> dict:
        if ipfs_jsu.exists_local_json_file(self._cache_dir, json_hash):
            return ipfs_jsu.load_local_json_file(self._cache_dir, json_hash)
        json_dict = ipfs_jsu.load_json_object(json_hash, self._gateway_url)
        ipfs_jsu.store_local_json_file(selff._cache_dir, json_hash, json_dict)
        return json_dict

    def store(self, json_dict: dict) -> str:
        json_hash = ipfs_jsu.store_json_object(json_dict, self._rpc_api_url_upload)
        ipfs_jsu.store_local_json_file(self._cache_dir, json_hash, json_dict)
        return json_hash

    def exists(self, json_hash: str) -> bool:
        return ipfs_jsu.exists_json_object(json_hash, self._gateway_url)

    def compute_hash(self, json_dict: dict) -> str:
        # TODO: A bit awkward to invoke an RPC endpoint to obtain the content identifier.
        #       It would be better to accomplish this locally.
        return ipfs_jsu.compute_hash(json_dict, self._rpc_api_url)
