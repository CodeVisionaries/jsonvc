from typing import Union
import orjson
from pathlib import Path
from .checksum import (
    is_hexadecimal,
    compute_json_hash,
    is_hash_wellformed,
)


def check_json_hash_wellformed(json_hash: str) -> bool:
    if not is_hash_wellformed(json_hash):
        raise ValueError('hash string is not well-formed')


def is_filename_wellformed(filename: Path) -> bool:
    f = Path(filename)
    if not f.suffix == '.json':
        return False
    if not len(f.stem) == 64:
        return False
    try:
        int(f.stem, 16)
    except ValueError:
        return False
    return True


def construct_filepath(json_hash: str, storage_dir: Path) -> str:
    return Path(storage_dir) / (json_hash + '.json')


def load_json_file(filepath: Path) -> dict:
    try:
        with open(Path(filepath), 'r') as f:
            json_dict = orjson.loads(f.read())
    except orjson.JSONDecodeError as e:
        raise orjson.JSONDecodeError('Invalid JSON file', e.doc, e.pos)
    return json_dict


def is_json_object_stored(json_hash: str, storage_dir: Path):
    check_json_hash_wellformed(json_hash)
    filepath = construct_filepath(json_hash, storage_dir) 
    return filepath.is_file()


def load_json_object(json_hash: str, storage_dir: Path) -> dict:
    """Load JSON object from content-addressable storage."""
    check_json_hash_wellformed(json_hash)
    filepath = construct_filepath(json_hash, storage_dir)
    json_dict = load_json_file(filepath)
    if json_hash != compute_json_hash(json_dict):
        raise ValueError('JSON object compromised')
    return json_dict


def store_json_object(json_dict: dict, storage_dir: Path) -> None:
    """Store JSON object in content-addressable storage"""
    json_hash = compute_json_hash(json_dict)
    if is_json_object_stored(json_hash, storage_dir):
        load_json_object(json_hash, storage_dir)
        return json_hash
    filepath = construct_filepath(json_hash, storage_dir) 
    with open(filepath, 'wb') as f:
        f.write(orjson.dumps(json_dict, option=orjson.OPT_SORT_KEYS))
    return json_hash
