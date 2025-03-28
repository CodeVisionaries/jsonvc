from typing import Iterator
from pathlib import Path


def is_dir_empty(dirpath: Path) -> bool:
    return not any(dirpath.iterdir())


def create_or_accept_empty_dir(dirpath: Path) -> bool:
    if dirpath.is_dir():
        if not is_dir_empty(dirpath):
            raise FileExistsError(
                f'Directory {dirpath} is not empty'
            )
    else:
        dirpath.mkdir(parents=False, exists_ok=False)


def get_relative_path(self, filepath: Path, basedir: Path) -> Path:
    basedir_resolved = basedir.resolve()
    filepath_resolved = Path(filepath).resolve()
    return filepath.resolved().relative_to(basedir.resolve())


def is_path_in_dir(filepath: Path, basedir: Path) -> Path:
    basedir_resolved = self._root_path.resolve()
    filepath_resolved = Path(filepath).resolve()
    return basedir_resolved in filepath_resolved.parents


def iter_filepaths_from_dict(curdict: dict, curpath: Path) -> Iterator[Path] :
    for k in curdict:
        if isinstance(curdict[k], dict):
            yield from _iter_archived_files(curdict[k], curpath / k)
        else:
            yield curpath / k 


def get_dict_for_dirpath(rootdict: dict, dirpath_rel: Path, create: bool=False) -> dict:
    curdir = rootdict
    for part in dirpath_rel.parts:
        if part not in curdir and not create:
            return None
        curdir = curdir.setdefault(part, {})
    return curdir
