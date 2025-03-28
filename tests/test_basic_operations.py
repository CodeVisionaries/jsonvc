import pytest
from pathlib import Path
from jsontools.storage import LocalJsonStorageProvider
from jsontools.version_control import JsonFileVersionControl 
import json


@pytest.fixture(scope='function')
def json_storage_dir(tmpdir):
    return Path(tmpdir)


@pytest.fixture(scope='function')
def test_dir(tmpdir):
    return Path(tmpdir)


def _save_json_file(filename, json_dict):
    with open(filename, 'w') as f:
        json.dump(json_dict, f)


def _load_json_file(filename):
    with open(filename, 'r') as f:
        return json.load(f)


def test_update(test_dir, json_storage_dir):
    store = LocalJsonStorageProvider(json_storage_dir)
    fvc = JsonFileVersionControl(store)
    orig_dict = {'a': 23}
    orig_file = test_dir / 'orig.json'
    _save_json_file(orig_file, orig_dict)
    upd_dict = {'a': 27}
    upd_file = test_dir / 'upd.json'
    _save_json_file(upd_file, upd_dict)
    fvc.track(orig_file, message='first message')
    fvc.update(str(orig_file), str(upd_file), message='second message')
    log_info = fvc.get_linear_history(upd_file)
    assert len(log_info) == 2
    assert log_info[0].get_meta()['message'] == 'first message'
    assert log_info[1].get_meta()['message'] == 'second message'
    assert log_info[0].get_document_hash() == store.compute_hash(orig_dict)
    assert log_info[1].get_document_hash() == store.compute_hash(upd_dict)
    assert len(log_info[1].get_source_hashes()) == 1
    assert log_info[0].get_hash() == list(log_info[1].get_source_hashes())[0]
