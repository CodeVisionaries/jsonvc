from typing import Callable, Optional
import orjson
import hashlib

import time


def is_hexadecimal(numstr: str) -> bool:
    """Check if string qualifies as hexadecimal number"""
    try:
        int(numstr, 16)
        return True
    except ValueError:
        return False


def is_hash_wellformed(numstr: str) -> bool:
    return is_hexadecimal(numstr) and len(numstr) == 64


def is_hash_prefix_wellformed(numstr: str) -> bool:
    return is_hexadecimal(numstr)


def get_unique_json_repr(json_dict: dict) -> str:
    """Return a compact and unique JSON string representation"""
    return orjson.dumps(json_dict, option=orjson.OPT_SORT_KEYS).decode('utf-8')


def compute_hash(data: str, algo='sha256') -> str:
    """Compute a cryptographic hash of a string"""
    algo_map = {'sha256': hashlib.sha256}
    return algo_map[algo](data.encode('utf8')).hexdigest()


def compute_json_hash(json_dict: dict, algo='sha256') -> str:
    """Compute a cryptographic hash for a JSON dictionary"""
    json_repr = get_unique_json_repr(json_dict)
    return compute_hash(json_repr, algo)


def normalize_json_dict(json_dict: dict) -> dict:
    return orjson.loads(get_unique_json_repr(json_dict))
