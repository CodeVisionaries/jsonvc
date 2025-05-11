from pathlib import Path
import orjson
import requests
import tempfile
from .checksum import get_unique_json_repr
from io import BytesIO


def exists_local_json_file(filedir: Path, filename: str) -> bool:
    filepath = Path(filedir) / filename
    return filepath.is_file()


def load_local_json_file(filedir: Path, filename: str) -> dict:
    filepath = Path(filedir) / filename
    with open(filepath, 'r') as f:
        json_dict = orjson.loads(f.read())
    return json_dict


def store_local_json_file(filedir: Path, filename: str, json_dict: dict):
    jsonstr = get_unique_json_repr(json_dict)
    filepath = Path(filedir) / filename
    with open(filepath, 'w') as f:
        f.write(jsonstr)


def exists_json_object(json_hash: str, gateway_url: str) -> bool:
    url = gateway_url.rstrip('/') + '/ipfs/' + json_hash
    response = requests.head(url, allow_redirects=True)
    return response.status_code == 200


def load_json_object(json_hash: str, gateway_url:str) -> dict:
    url = gateway_url.rstrip('/') + '/ipfs/' + json_hash
    response = requests.get(url, stream=False)
    if response.status_code != 200:
        raise Exception(f'failed to fetch CID {json_hash}: HTTP {response.status_code}')
    return response.text


def _store_json_object(json_dict: dict, rpc_api_url: str, only_hash: bool=False) -> str:
    jsonstr = get_unique_json_repr(json_dict)
    json_bytes = jsonstr.encode('utf-8')
    file_obj = BytesIO(json_bytes)
    files = {'file': ('dummy', file_obj)}
    ipfs_add_url = rpc_api_url.rstrip('/') + '/v0/add'
    params = {'only-hash': only_hash}
    response = requests.post(ipfs_add_url, params=params, files=files)
    if response.status_code != 200:
        if only_hash:
            message_prefix = 'CID determination failed'
        else:
            message_prefix = 'Upload filed'
        raise Exception(f'{message_prefix}: HTTP {response.status_code} - {response.text}')
    return response.json()['Hash']


def store_json_object(json_dict: dict, rpc_api_url: str):
    return _store_json_object(json_dict, rpc_api_url, only_hash=False)


def compute_hash(json_dict: dict, rpc_api_url: str):
    return _store_json_object(json_dict, rpc_api_url, only_hash=True)
