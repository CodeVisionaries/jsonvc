import jsonpatch
import json
from copy import deepcopy
from typing import Callable
from .json.base_models import ExtJsonPatchBase
from .checksum import compute_json_hash


def create_patch(old_json_dict: dict, new_json_dict: dict) -> list:
    return json.loads(
        jsonpatch.make_patch(old_json_dict, new_json_dict).to_string()
    )


def create_ext_patch(old_json_dict: dict, new_json_dict: dict) -> list:
    old_hash = compute_json_hash(old_json_dict)
    old_ext_dict = {'object': old_json_dict}
    new_ext_dict = {'object': new_json_dict}
    patch = create_patch(old_ext_dict, new_ext_dict)
    return ExtJsonPatchBase(
        sourceHashes={'object': old_hash}, target='object', operations=patch
    ).model_dump()


def apply_patch(json_dict: dict, json_patch: list, inplace=False) -> dict: 
    """Apply a JSON patch to a JSON dict"""
    if not inplace:
        json_dict = deepcopy(json_dict)
    patch = jsonpatch.JsonPatch(json_patch)
    return patch.apply(json_dict, in_place=inplace)


def apply_ext_patch(ext_json_patch: dict, retrieve_func: Callable) -> dict:
    """Apply an extended JSON patch with multiple sources

    Expects `ext_json_patch` to contain fields `sources`, `target` and
    `operations`. `sources` is a dictionary with keys representing
    aliases for the JSON objects serving as input to the extended JSON
    patch. These keys are associated with strings that contain the JSON hashes
    of the source JSON objects, unambiguously determining their identity. 
    The key `target` is associated with either the `None` value or a string 
    identical to one of the aliases defined in `sources`.
    The JSON patch is provided under `operations` and will be applied
    to the `sources` dictionary. The dictionary under the alias specified
    by `target` will be returned.
    For instance,
    {
      'sources': {
        'json_obj1': { ... },
        'json_obj2': { ... }
      },
      'target': 'json_obj1' 
    }

    One operation of the JSON patch could copy content from
    /json_obj1/some_key to /target/some_other_key

    The function returns the JSON dictionary associated with the
    `target` key after the application of the JSON patch.
    """
    ExtJsonPatchBase.model_validate(ext_json_patch)
    source_hashes  = ext_json_patch['sourceHashes']
    target = ext_json_patch['target']
    json_patch = ext_json_patch['operations']
    sources_dict = {
        source_alias: retrieve_func(json_hash)
        for source_alias, json_hash in source_hashes.items()
    }
    patch_update = apply_patch(sources_dict, json_patch) 
    return patch_update[target]
