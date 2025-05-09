from typing import Callable, List, Dict, Optional
import json
from .jsonpatch_ext import (
    create_patch,
    apply_patch,
    create_ext_patch,
)
from .checksum import (
    is_hash_prefix_wellformed,
)
from pathlib import Path
from .json.models import JsonGraphNode, ExtJsonPatch
from .storage_utils import load_json_file
from .storage import (
    JsonStorageProvider,
    JsonObjectIndex,
)
from .custom_exceptions import (
    HashPrefixAmbiguousError,
    HashNotFoundError,
    DocAlreadyTrackedError,
    SeveralAncestorsError,
    SeveralNodesWithDocError,
    DocNotTrackedError,
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
            hash_func = self._storage.compute_hash,
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
            source_node = JsonGraphNode(
                hash_func = self._storage.compute_hash,
                **self._storage.load(snh)
            )
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
            hash_func = self._storage.compute_hash,
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

    def to_dict(self):
        known_nodes = {h: sorted(v) for h, v in self._known_nodes.items()}
        known_docs = {h: sorted(v) for h, v in self._known_docs.items()}
        return {
            'known_nodes': known_nodes,
            'known_docs': known_docs,
        }

    def from_dict(self, cache_dict, update=True):
        known_nodes = {h: set(v) for h, v in cache_dict['known_nodes'].items()}
        known_docs = {h: set(v) for h, v in cache_dict['known_docs'].items()}
        if update:
            self._known_nodes.update(known_nodes)
            self._known_docs.update(known_docs)
        else:
            self._known_nodes = known_nodes
            self._known_docs = known_docs

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
        cur_node = JsonGraphNode(
            hash_func=self._storage.compute_hash,
            **self._storage.load(node_hash)
        )
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

    def find_associated_node_hashes(self, doc_hash: str) -> List[str]:
        return self._known_docs.get(doc_hash, set()).copy()

    def get_doc_hashes(self) -> list[str]:
        return list(self._known_docs)

    def get_node_hashes(self) -> list[str]:
        return list(self._known_nodes)

    def get_node_ancestor_hashes(self, node_hash) -> list[str]:
        return self._known_nodes[node_hash]

    def get_node(self, node_hash: str) -> JsonGraphNode:
        self.update(node_hash)
        return JsonGraphNode(
            hash_func = self._storage.compute_hash,
            **self._storage.load(node_hash)
        )


class JsonDocVersionControl:

    def __init__(self, storage_provider: JsonStorageProvider) -> None:
        if not isinstance(storage_provider, JsonStorageProvider):
            raise TypeError(
                'argument `storage provider` must be instance of `JsonStorageProvider`'
            )
        self._graph = JsonTrackGraph(storage_provider)
        self._cache = JsonNodeCache(storage_provider)
        self._storage = storage_provider

    # methods taking json dicts as input

    def get_associated_node_hashes(self, json_dict: dict) -> list[str]:
        json_hash = self._storage.compute_hash(json_dict)
        return self._cache.find_associated_node_hashes(json_hash)

    def is_tracked(self, json_dict: dict) -> bool:
        node_hashes = self.get_associated_node_hashes(json_dict)
        return len(node_hashes) > 0

    def track(self, json_dict: dict, message: str, force: bool=False) -> str:
        if self.is_tracked(json_dict) and not force:
            raise DocAlreadyTrackedError('The JSON document is already being tracked')
        meta = {'message': message}
        node_hash = self._graph.create_genesis_node(json_dict, meta)
        self._cache.update(node_hash)
        return node_hash

    # methods taking node hashes as inputs

    def get_messages(self, node_hashes: list[str]) -> dict[str, str]:
        nodes = [self._cache.get_node(h) for h in node_hashes]
        messages = {h: n.get_meta()['message'] for h, n in zip(node_hashes, nodes)}
        return messages

    def update(self, old_node_hash: dict, new_json_dict: dict,
               message: str, force: bool=False) -> str:
        if self.is_tracked(new_json_dict) and not force:
            raise DocAlreadyTrackedError('The new JSON document is already in the system')
        old_json_dict = self.get_doc(old_node_hash)
        hash_func = self._storage.compute_hash
        ext_patch = create_ext_patch(old_json_dict, new_json_dict, hash_func)
        meta = {'message': message}
        new_doc_hash = self._storage.compute_hash(new_json_dict)
        source_node_hashes = [old_node_hash]
        new_node = self._graph.create_node(
            ext_patch, source_node_hashes, meta, new_doc_hash
        )
        self._cache.update(new_node)
        return new_node

    def get_linear_history(self, node_hash: str) -> list[JsonGraphNode]:
        node_hashes = [node_hash]
        nodes = []
        while len(node_hashes) > 0:
            # TODO: extend log show capability to deal with merge commits
            if len(node_hashes) > 1:
                raise SeveralAncestorsError('Several ancestors detected', node_hashes)
            cur_node_hash = list(node_hashes)[0]
            cur_node = self._cache.get_node(cur_node_hash)
            nodes.append(cur_node)
            node_hashes = self._cache.get_node_ancestor_hashes(cur_node_hash)
        return nodes[::-1]

    def get_doc(self, node_hash: str) -> dict:
        node = self._cache.get_node(node_hash)
        doc_hash = node.get_document_hash()
        return self._storage.load(doc_hash)

    # auxiliary (but essential) functions for class users

    def expand_hash_prefix(self, hash_prefix: str) -> dict:
        node_hashes = self._cache.get_node_hashes()
        matches = [n for n in node_hashes if n.startswith(hash_prefix)]
        if len(matches) == 0:
            raise HashNotFoundError('No node registered under the hash provided')
        elif len(matches) > 1:
            raise HashPrefixAmbiguousError(
                'Shortform hash ambiguous---provide more leading characters'
            )
        return matches[0]

    def get_diff(self, old_json_dict, new_json_dict):
        patch = create_patch(old_json_dict, new_json_dict)
        # for the time being, apply the created patch and
        # see if the new document is recovered. This careful
        # measure is due to issues, such as #138, #152, #160
        # reported at https://github.com/stefankoegl/python-json-patch/issues
        test_doc = apply_patch(old_json_dict, patch)
        new_json_hash = self._storage.compute_hash(new_json_dict)
        test_hash = self._storage.compute_hash(test_doc)
        if new_json_hash != test_hash:
            raise ValueError(
                'An invalid patch has been created for the comparison. This '
                'error is likely the result of a bug in the jsonpatch package.'
            )
        return patch


class JsonFileVersionControl:

    def __init__(self, storage_provider: JsonStorageProvider) -> None:
        self._docvc = JsonDocVersionControl(storage_provider)

    def _get_hash_from_objref(self, json_objref: str, source: str='any') -> None:
        if source in ('any', 'file'):
            try:
                json_dict = load_json_file(json_objref)
                node_hashes = self._docvc.get_associated_node_hashes(json_dict)
                if len(node_hashes) == 0:
                    raise DocNotTrackedError('JSON document not tracked in the system')
                if len(node_hashes) > 1:
                    raise SeveralNodesWithDocError(
                        'Encountered several Nodes associated with the same JSON document',
                        node_hashes
                    )
                return list(node_hashes)[0]
            except json.decoder.JSONDecodeError:
                raise ValueError(
                    f'The file `{f}` is not in JSON format.'
                )
            except FileNotFoundError as exc:
                if source == 'file':
                    raise
        if source in ('any', 'cache'):
            return self._docvc.expand_hash_prefix(json_objref)
        raise ValueError('argument `source` must be one of `any`, `file`, `cache`')

    def _get_doc_from_objref(self, json_objref: str, source: str='any') -> dict:
        if source in ('any', 'file'):
            try:
                return load_json_file(json_objref)
            except FileNotFoundError:
                if source == 'file':
                    raise
        if source in ('any', 'cache'):
            node_hash = self._docvc.expand_hash_prefix(json_objref)
            return self._docvc.get_doc(node_hash)
        raise ValueError('argument `source` must be one of `any`, `file`, `cache`')

    def get_associated_node_hashes(self, json_file: Path) -> list[str]:
        json_dict = load_json_file(json_file)
        return self._docvc.get_associated_node_hashes(json_dict)

    def get_messages(self, json_file: Path) -> dict[str, str]:
        node_hashes = self.get_associated_node_hashes(json_file)
        return self._docvc.get_messages(node_hashes)

    def is_tracked(self, json_file: Path) -> bool:
        json_dict = load_json_file(Path(json_file))
        return self._docvc.is_tracked(json_dict)

    def track(self, json_file: Path, message: str, force: bool=False) -> str:
        json_dict = load_json_file(Path(json_file))
        return self._docvc.track(json_dict, message, force)

    def update(self, old_json_objref: str, new_json_objref: Path,
               message: str, force: bool=False) -> str:
        old_node_hash = self._get_hash_from_objref(old_json_objref)
        new_json_dict = self._get_doc_from_objref(new_json_objref, source='any')
        return self._docvc.update(old_node_hash, new_json_dict, message, force)

    def replace(self, target_json_file: Path, update_json_file: Path,
                message: str, force: bool=False, target_hash_prefix: Optional[str]=None) -> str:
        if target_hash_prefix is None:
            target_node_hash = self._get_hash_from_objref(str(target_json_file), source='file')
        else:
            target_node_hashes = self.get_associated_node_hashes(target_json_file)
            target_node_hash_matches = [
                t for t in target_node_hashes
                if t.startswith(target_hash_prefix)
            ]
            if len(target_node_hash_matches) > 1:
                raise HashPrefixAmbiguousError(
                    'The hash prefix matches several node hashes'
                )
            if len(target_node_hash_matches) == 0:
                raise ValueError('Invalid target_node_hash provided')
            target_node_hash = target_node_hash_matches[0]
        new_json_dict = self._get_doc_from_objref(str(update_json_file), source='file')
        ret = self._docvc.update(target_node_hash, new_json_dict, message, force)
        update_json_file.replace(target_json_file)
        return ret

    def get_linear_history(self, json_objref: str) -> list[JsonGraphNode]:
        node_hash = self._get_hash_from_objref(json_objref)
        linear_history = self._docvc.get_linear_history(node_hash)
        return linear_history

    def get_doc(self, json_objref: str, json_dumps_args: Optional[dict]=None) -> str:
        json_dict = self._get_doc_from_objref(json_objref, source='cache')
        return json.dumps(json_dict, **json_dumps_args)

    def get_diff(self, old_json_objref: str, new_json_objref: str,
                 json_dumps_args: Optional[dict]=None) -> str:
        old_json_dict = self._get_doc_from_objref(old_json_objref)
        new_json_dict = self._get_doc_from_objref(new_json_objref)
        diff_dict = self._docvc.get_diff(old_json_dict, new_json_dict)
        return json.dumps(diff_dict, **json_dumps_args)
