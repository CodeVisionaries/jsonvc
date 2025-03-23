from typing import List
from .base_models import (
    ExtJsonPatchBase,
    JsonGraphNodeBase,
)
from ..jsonpatch_ext import apply_ext_patch
from ..checksum import compute_json_hash


def _none_to_list(obj):
    return obj if obj is not None else []


def _none_to_dict(obj):
    return obj if obj is not None else {} 


class ExtJsonPatch:

    def __init__(self, *args, **kwargs) -> None:
        source_hashes = kwargs.get('sourceHashes', None)
        if source_hashes is not None:
            # normalization: put keys into leixcographic order 
            sorted_dict = {}
            for k in sorted(source_hashes):
                sorted_dict[k] = source_hashes[k] 
            kwargs['sourceHashes'] = sorted_dict
        self._datamodel = ExtJsonPatchBase(*args, **kwargs)

    def __hash__(self) -> int:
        return int(self.get_hash(), 16)

    def get_hash(self) -> str:
        return compute_json_hash(self.model_dump())

    def get_source_hashes(self) -> list:
        return list(self._datamodel.sourceHashes.values())

    def apply(self, load_json_func: callable):
        json_dict = self.model_dump()
        return apply_ext_patch(json_dict, load_json_func)

    def model_dump(self) -> dict:
        return self._datamodel.model_dump()


class JsonGraphNode:

    def __init__(self, *args, **kwargs) -> None:
        source_hashes = kwargs['sourceHashes']
        if source_hashes is not None:
            # normalization: sort source node hashes lexicographically
            source_node_hashes = sorted(set(source_hashes))
            kwargs['sourceHashes'] = source_hashes
        self._datamodel = JsonGraphNodeBase(*args, **kwargs)

    def get_ext_patch_hash(self) -> str:
        return self._datamodel.extJsonPatchHash

    def get_source_hashes(self) -> List[str]:
        return set(_none_to_list(self._datamodel.sourceHashes))

    def __hash__(self) -> int:
        # NOTE: calling hash(obj) truncates the result
        #       compared to calling obj.__hash__()
        return int(self.get_hash(), 16) 

    def get_hash(self) -> str:
        return compute_json_hash(self.model_dump())

    def get_document_hash(self) -> List[str]:
        return self._datamodel.documentHash

    def get_meta(self) -> dict:
        return _none_to_dict(self._datamodel.meta)

    def model_dump(self) -> dict:
        return self._datamodel.model_dump()
