from jsontools.storage import LocalJsonStorageProvider
from jsontools.json.models import JsonGraphNode
from jsontools.checksum import compute_json_hash, normalize_json_dict
from jsontools.version_control import (
    JsonTrackGraph,
    JsonNodeCache,
    JsonDocVersionControl,
)
from jsontools.jsonpatch_ext import create_ext_patch


store = LocalJsonStorageProvider('storage/')
docvc = JsonDocVersionControl(store)

first_obj = {'b': 7, 'a': 5}
second_obj = {'a': 7, 'b': [1,2]}
third_obj = {'x': 5, 'a': 4} 

docvc.is_tracked(first_obj)
docvc.is_tracked(second_obj)
docvc.is_tracked(third_obj)

docvc.track(first_obj, 'adding my first document')
docvc.track(second_obj, 'adding my second document')

docvc.update(first_obj, third_obj, 'now we modify the first document to obtain the third') 

docvc.get_log(third_obj)
