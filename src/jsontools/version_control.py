from typing import Callable, List, Dict, Optional
import json
from .jsonpatch_ext import (
    create_patch,
    apply_patch,
    create_ext_patch,
)
from .checksum import compute_json_hash
from pathlib import Path
from .json.models import JsonGraphNode, ExtJsonPatch
from .storage_utils import load_json_file
from .storage import (
    JsonStorageProvider,
    JsonObjectIndex,
)


class JsonTrackGraph:

    def __init__(self, storage_provider: JsonStorageProvider):
        self._storage = storage_provider 

    def get_storage_provider(self) -> JsonStorageProvider:
        return self._storage

    def create_genesis_node(self, json_dict: dict, meta: Optional[dict]=None) -> str:
        doc_hash = self._storage.store(json_dict)
        genesis_node = JsonGraphNode(
            extJsonPatchHash = None,
            documentHash = doc_hash,
            sourceHashes = None, 
            meta = meta,
        )
        # update cache
        node_hash = self._storage.store(genesis_node.model_dump())
        return node_hash

    def create_node(
        self, ext_json_patch: dict, source_hashes: List[str],
        meta: Optional[dict]=None, expected_doc_hash: Optional[str]=None
    ) -> str:
        # do rigorous consistency checking
        patch = ExtJsonPatch(**ext_json_patch)
        patch_source_hashes = patch.get_source_hashes()
        doc_map = {} 
        for snh in source_hashes:
            source_node = JsonGraphNode(**self._storage.load(snh))
            doc_hash = source_node.get_document_hash()
            doc_map[doc_hash] = snh 
        if set(patch_source_hashes) != set(doc_map):
            raise ValueError(
                'Document sources in extended json patch are '
                'inconsistent with document hashes of source nodes'
            )
        # apply the patch and store new JSON doc, ext JSON patch and graph node
        new_doc = patch.apply(self._storage.load)
        patch_hash = self._storage.store(patch.model_dump())
        new_doc_hash = self._storage.store(new_doc)
        if new_doc_hash != expected_doc_hash:
            raise ValueError(
                'The hash of the new document is not equal to the '
                'expected hash. This error may indicate that the jsonpatch '
                'package has created an inapropriate patch to transform a '
                'given source document into a given destination document.'
            )
        new_node = JsonGraphNode(
            extJsonPatchHash = patch_hash,
            documentHash = new_doc_hash,
            sourceHashes = source_hashes,
            meta = meta,
        )
        new_node_hash = self._storage.store(new_node.model_dump())
        return new_node_hash


class JsonNodeCache:

    def __init__(self, storage_provider: JsonStorageProvider) -> None:
        self._storage = storage_provider
        self._known_nodes = dict()
        self._known_docs = dict()
        self._unavail_nodes = set()
        self._should_skip = lambda h: False
        if isinstance(storage_provider, JsonObjectIndex):
            self._should_skip = lambda h: self._storage.size(h) > 1000
            self.discover_nodes(self._storage.index())

    def get_storage_provider(self) -> JsonStorageProvider:
        return self._storage

    def update_doc_cache(self, doc_hash: str, node_hash: str) -> None:
        """Register node hash under its associated JSON doc hash."""
        # NOTE: Several distinct nodes may be associated with the
        #       same JSON document.
        blocks_linked_to_doc = (
            self._known_docs.setdefault(doc_hash, set())
            )
        blocks_linked_to_doc.add(node_hash)

    def update_node_cache(self, node_hash: str, child_hashes: List[str]) -> None:
        """Register node hash and associated ancestor hashes"""
        cached_child_hashes = self._known_nodes.setdefault(node_hash, set())
        cached_child_hashes.update(child_hashes)

    def update(self, node_hash: str) -> JsonGraphNode:
        if node_hash in self._known_nodes:
            return
        if not self._storage.exists(node_hash):
            self._unavail_nodes.add(node_hash)
            return
        if node_hash in self._unavail_nodes:
            self._unavail_nodes.remove(node_hash)
        # node is available and we can query
        # information and cache it.
        cur_node = JsonGraphNode(**self._storage.load(node_hash))
        # Here the function will fail if the node is not a valid JsonGraphNode
        source_node_hashes = cur_node.get_source_hashes() 
        self._known_nodes[node_hash] = source_node_hashes
        cur_doc_hash = cur_node.get_document_hash()
        self.update_doc_cache(cur_doc_hash, node_hash)
        self.update_node_cache(node_hash, source_node_hashes)

    def discover_nodes(self, seed_node_hashes: List[str]):
        for node_hash in seed_node_hashes:
            if self._should_skip(node_hash):
                continue
            try:
                self.update(node_hash)
            except Exception:  # TODO: more fine-grained exception handling
                continue
            source_node_hashes = self._known_nodes[node_hash]
            nodes_to_visit = source_node_hashes.difference(self._known_nodes)
            self.discover_nodes(nodes_to_visit)

    def find_associated_nodes(self, doc_hash: str) -> List[str]:
        return self._known_docs.get(doc_hash, set()).copy()

    def get_doc_hashes(self) -> list[str]:
        return list(self._known_docs)

    def get_node_hashes(self) -> list[str]:
        return list(self._known_nodes)

    def get_node_ancestor_hashes(self, node_hash) -> list[str]:
        return self._known_nodes[node_hash]

    def get_node(self, node_hash: str) -> JsonGraphNode:
        self.update(node_hash)
        return JsonGraphNode(**self._storage.load(node_hash))


class JsonDocVersionControl:

    def __init__(self, storage_provider: JsonStorageProvider) -> None:
        self._graph = JsonTrackGraph(storage_provider)
        self._cache = JsonNodeCache(storage_provider)
        self._storage = storage_provider

    def get_associated_node_hashes(self, json_dict: dict) -> str:
        json_hash = compute_json_hash(json_dict)
        return self._cache.find_associated_nodes(json_hash)

    def is_tracked(self, json_dict: dict) -> bool:
        json_hash = compute_json_hash(json_dict)
        node_hashes = self._cache.find_associated_nodes(json_hash)
        return len(node_hashes) > 0 

    def track(self, json_dict: dict, comment: Optional[str]=None) -> str:
        if self.is_tracked(json_dict):
            raise ValueError('already tracked')
        meta = {'comment': str(comment)} if comment is not None else None 
        node_hash = self._graph.create_genesis_node(json_dict, meta)
        self._cache.update(node_hash)
        return node_hash

    def update(self, old_json_dict: dict, new_json_dict: dict, comment: Optional[str]=None) -> str:
        if not self.is_tracked(old_json_dict):
            raise FileNotFoundError('The JSON object to be updated is not tracked')
        if self.is_tracked(new_json_dict):
            raise ValueError('The new JSON file is already in the system')
        ext_patch = create_ext_patch(old_json_dict, new_json_dict)
        doc_hash = compute_json_hash(old_json_dict)
        source_node_hashes = self._cache.find_associated_nodes(doc_hash)
        if len(source_node_hashes) > 1:
            raise ValueError('more than one node are associated with this JSON document')
        meta = {'comment': str(comment)} if comment is not None else None 
        new_doc_hash = compute_json_hash(new_json_dict)
        new_node = self._graph.create_node(
            ext_patch, source_node_hashes, meta, new_doc_hash
        )
        self._cache.update(new_node)
        return new_node

    def get_log(self, json_dict: dict) -> list[str]:
        if not self.is_tracked(json_dict):
            raise IndexError('This JSON object is not tracked, no log available')
        doc_hash = compute_json_hash(json_dict)
        node_hashes = self._cache.find_associated_nodes(doc_hash)
        comments = []
        while len(node_hashes) > 0:
            # TODO: extend log show capability to deal with merge commits
            if len(node_hashes) > 1:
                raise IndexError('Ambiguous log: More than one node associated with this document')
            cur_node_hash = list(node_hashes)[0]
            cur_node = self._cache.get_node(cur_node_hash)
            meta = cur_node.get_meta()
            comment = meta.get('comment', '')
            comments.append(f"{cur_node_hash[:7]}: {comment}")
            node_hashes = self._cache.get_node_ancestor_hashes(cur_node_hash)
        return comments[::-1]

    def _get_full_node_hash(self, short_node_hash: str) -> dict:
        node_hashes = self._cache.get_node_hashes() 
        matches = [n for n in node_hashes if n.startswith(short_node_hash)]
        if len(matches) == 0:
            raise IndexError('No node registered under the hash provided')
        elif len(matches) > 1:
            raise IndexError('Shortform hash ambiguous---provide more leading characters')
        return matches[0]

    def get_doc(self, short_node_hash: str) -> dict:
        node_hash = self._get_full_node_hash(short_node_hash)
        node = self._cache.get_node(node_hash)
        doc_hash = node.get_document_hash()
        return self._storage.load(doc_hash)

    def get_diff(self, old_short_node_hash, new_short_node_hash):
        old_node_hash = self._get_full_node_hash(old_short_node_hash)
        new_node_hash = self._get_full_node_hash(new_short_node_hash)
        old_node = self._cache.get_node(old_node_hash)
        new_node = self._cache.get_node(new_node_hash)
        old_doc_hash = old_node.get_document_hash()
        new_doc_hash = new_node.get_document_hash()
        old_json_dict = self._storage.load(old_doc_hash)
        new_json_dict = self._storage.load(new_doc_hash)
        patch = create_patch(old_json_dict, new_json_dict)
        # for the time being, apply the created patch and
        # see if the new document is recovered. This careful
        # measure is due to issues, such as #138, #152, #160
        # reported at https://github.com/stefankoegl/python-json-patch/issues
        test_doc = apply_patch(old_json_dict, patch)
        if compute_json_hash(new_json_dict) != compute_json_hash(test_doc):
            raise ValueError(
                'An invalid patch has been created for the comparison. This '
                'error is likely the result of a bug in the jsonpatch package.'
            )
        return patch


class JsonFileVersionControl:

    def __init__(self, storage_provider: JsonStorageProvider) -> None:
        self._docvc = JsonDocVersionControl(storage_provider)

    def get_associated_node_hashes(self, json_file: Path) -> str:
        json_dict = load_json_file(json_file)
        return self._docvc.get_associated_node_hashes(json_dict)

    def is_tracked(self, json_file: Path) -> bool:
        node_hashes = self.get_associated_node_hashes(json_file)
        return len(node_hashes) > 0 

    def track(self, json_file: Path, comment: Optional[str]=None) -> str:
        json_dict = load_json_file(json_file)
        return self._docvc.track(json_dict, comment)

    def update(self, old_json_file: Path, new_json_file: Path, comment: Optional[str]=None) -> str:
        old_json_dict = load_json_file(old_json_file)
        new_json_dict = load_json_file(new_json_file)
        return self._docvc.update(old_json_dict, new_json_dict, comment)

    def get_log(self, json_file: Path) -> list[str]:
        json_dict = load_json_file(json_file)
        return self._docvc.get_log(json_dict)

    def get_doc(self, short_node_hash: str, json_dumps_args: Optional[dict]=None) -> str:
        json_dict = self._docvc.get_doc(short_node_hash)
        return json.dumps(json_dict, **json_dumps_args)

    def get_diff(self, old_short_node_hash: str, new_short_node_hash: str) -> str:
        json_dict = self._docvc.get_diff(old_short_node_hash, new_short_node_hash)
        return json.dumps(json_dict, indent=2)
