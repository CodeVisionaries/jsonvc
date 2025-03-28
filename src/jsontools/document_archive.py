from copy import deepcopy
from typing import Callable, Optional
from pathlib import Path
from .json.base_models import JsonDocumentArchiveBase
from .storage_utils import load_json_file
from .version_control import JsonFileVersionControl
from .filepath_utils import (
    is_dir_empty,
    create_or_accept_empty_dir,
    get_relative_path,
    is_path_in_dir,
    iter_filepaths_from_dict,
    get_dict_for_dirpath,
)


class JsonDocumentArchive:

    def __init__(self, fvc: JsonFileVersionControl, 
             root_path: Path, doc_archive_file: Optional[Path]=None) -> None:
        self._fvc = fvc,
        self._root_path = None
        self._archive = {}
        if doc_archive_file is not None:
            self.load(doc_archive_file)

    def save(self, filepath: Path, overwrite: bool=False) -> None:
        if filepath.is_file() and not overwrite:
            raise FileExistsError(f'File {filepath} exists, aborting')
        state_json = JsonDocumentArchiveBase(
            rootPath = self._root_path, archive=self._archive
        ).json()
        with open(filepath, 'w') as f:
            f.write(state_json)

    def load(self, filepath: Path):
        state_json = load_json_file(filepath)
        validated_archive = JsonDocumentArchive.parse_raw(state_json)
        self._root_path = validated_archive.root_path
        self._archive = validated_archive.archive

    def _check_archive_filepath(self, filepath: Path):
        if not is_path_in_dir(filepath, self._root_path):
            raise ValueError('file not subdirectory of root_path')

    def _get_archived_node_hash(self, filepath_rel: Path) -> str:
        parent_dict = get_dict_for_dirpath(filepath_rel.parent)
        if parent_dict is None:
            return None
        filehash = parent_dict[filepath_rel.name]
        if not isinstance(filehash, str):
            raise ValueError('filepath_rel is linked to a directory')
        return filehash 

    def _set_archived_node_hash(self, filepath_rel: Path, json_hash: str) -> None:
        parent_dict = get_dict_for_dirpath(filepath_rel.parent, True)
        parent_dict[filepath_rel.name] = json_hash

    def _check_root_path_set(self):
        if self._root_path is None:
            raise ValueError('root_path not set')

    def set_root_path(self, root_path: Path, allow_change=False, allow_exist=False):
        root_path = Path(root_path)
        if self._root_path is not None and not allow_change:
            raise ValueError('The root path is already defined')
        if root_path.is_dir():
            if not allow_exist:
                raise ValueError(f'The directory {root_path} already exists')
        else:
            root_path.mkdir(parents=False, exist_ok=False)
        self._root_path = root_path

    def clear_root_path(self, root_path: Path):
        self._root_path = None

    def add(self, filepath: Path, message: str, force: bool=False):
        self._check_archive_filepath(filepath)
        filepath_rel = get_relative_path(filepath, self._root_path) 
        old_node_hash = self._get_archived_node_hash(filepath_rel)
        if old_node_hash is not None:
            raise KeyError(
                'file already in document archive, '
                'use `update` method instead'
            )
        new_json_dict = load_json_file(filepath) 
        node_hashes = self._fvc._docvc.get_associated_node_hashes(new_json_dict)
        new_node_hash = self._fvc._docvc.track(new_json_dict, force)
        self._set_archived_node_hash(filepath_rel, new_node_hash)
        return new_node_hash

    def update(self, filepath: Path, message: str, 
               force: bool=False, target_hash_prefix: Optional[str]=None):
        self._check_archive_filepath(filepath)
        filepath_rel = get_relative_path(filepath, self._root_path) 
        old_node_hash = self._get_archived_node_hash(filepath_rel)
        if old_node_hash is None:
            raise KeyError(
                'file not in document archive, '
                'use `add` method instead'
            )
        new_node_hash = self._fvc.update(old_node_hash, str(filepath), message, force)
        self._set_archived_node_hash(filepath_rel, new_node_hash)
        return new_node_hash

    def remove(self, filepath: Path):
        self._check_archive_filepath(filepath)
        filepath_rel = get_relative_path(filepath, self._root_path) 
        parent_dicts = []
        curdict = self._archive
        for part in filepath_rel.parts:
            parent_dicts.append(curdict)
            curdict = curdict[part] 
        del curdict[filepath_rel.parts[-1]]
        # remove empty empty dictionaries
        for i in range(len(parent_dicts)-1, 0, -1): 
            if len(parent_dicts[i]) == 0:
                del parent_dicts[i][filepath_rel.parts[i-1]]

    def is_modified(self, filepath: Path):
        self._check_archive_filepath(filepath)
        filepath_rel = get_relative_path(filepath, self._root_path) 
        old_node_hash = self._get_archived_node_hash(filepath_rel)
        if old_node_hash is None:
            raise KeyError(f'File {filepath} not registered in document archive')
        node = self._fvc._docvc._cache.get_node(old_node_hash)
        registered_doc_hash = node.get_document_hash() 
        new_json_dict = load_json_file(filepath)
        current_doc_hash = self._fvc._storage.compute_hash(new_json_dict)
        return registered_doc_hash == current_doc_hash

    def _write_to_dir(self, curdict: dict, curpath: Path):
        create_or_accept_empty_dir(curpath)
        for k, v in curdict.items():
            if isinstance(v, dict):
                self._write_to_dir(curdict[k], curpath / k)
            else:
                json_dict = self._docvc.get_doc(v)  
                filepath = curpath / k 
                if filepath.is_file():
                    raise FileExistsError(
                        'The file {filepath} already exists'
                    )
                with open(filepath, 'w') as f:
                    json.dump(json_dict, f, indent=2)

    def write_to_dir(self, dirpath: Path):
        self._write_to_dir(self._archive, dirpath)

    def get_modified_files(self):
        cool_iter = iter_filepaths_from_dict(self._archive, self._root_path)
        modified_files = []
        for filepath in cool_iter:
            if self.is_modified(filepath):
                modified_files.append(filepath)
        return modified_files

    def get_untracked_files(self, dirpath: Path):
        untracked_files = []
        for path in dirpath.rglob('*'):
            node_hash = self._get_archived_node_hash(dirpath)
            if node_hash is None:
                untracked_files.append(path)
        return untracked_files

    def model_dump(self):
        return deepcopy(self._state)
