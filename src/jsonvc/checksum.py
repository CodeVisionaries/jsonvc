from typing import Callable, Optional
import json
import hashlib


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
    return json.dumps(
        json_dict, skipkeys=False, ensure_ascii=True,
        check_circular=True, allow_nan=False, indent=None,
        separators=(',',':'), sort_keys=True
    )


def compute_hash(data: str, algo='sha256') -> str:
    """Compute a cryptographic hash of a string"""
    algo_map = {'sha256': hashlib.sha256}
    return algo_map[algo](data.encode('utf8')).hexdigest()


def compute_json_hash(json_dict: dict, algo='sha256') -> str:
    """Compute a cryptographic hash for a JSON dictionary"""
    json_repr = get_unique_json_repr(json_dict)
    return compute_hash(json_repr, algo)


def normalize_json_dict(json_dict: dict) -> dict:
    return json.loads(get_unique_json_repr(json_dict))
