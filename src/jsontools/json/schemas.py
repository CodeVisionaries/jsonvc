__all__ = ['schema_list']

# schemas are appended after their definition
schema_list = []

# recurring property templates

_fieldname_regex = '^[0-9a-zA-Z_-]+$'
_content_id_regex = '^[0-9a-zA-Z]{40,}$'

_cid_property = lambda descr = None, optional=False: {
    k: v if not optional or k != 'type' else [v, 'null'] for k, v in {
        k: v for k, v in {
            'description': descr, 
            'type': 'string',
            'pattern': _content_id_regex
        }.items() if descr is not None or k != 'description'
    }.items()
}

_fieldname_property = lambda optional=False: {
    'description': 'Valid name for JSON attribute',
    'type': 'string' if not optional else ['string', 'null'],
    'pattern': _fieldname_regex,
}


# json schema definitions

json_graph_node_schema = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'version': '0.0.1',
    'title': 'JsonGraphNodeBase',
    'description': 'Stores reference to JSON object and to JSON patch that generated it',
    'type': 'object',
    'properties': {
        'extJsonPatchHash': _cid_property(
            'sha256 hexdigest of extJsonPatch document', optional=True
        ),
        'documentHash': _cid_property('sha256 hexdigest of associated JSON document'),
        'sourceHashes': {
            'description': 'List with source node hashes',
            'type': ['array', 'null'],
            'items': _cid_property('sha256 hash of source node'),
            'additionalProperties': False,
        },
        'meta': {
            'description': 'Additional optional meta information',
            'type': ['object', 'null'],
        }
    },
    'required': ['extJsonPatchHash', 'documentHash', 'sourceBlocks']
}
schema_list.append(json_graph_node_schema)


ext_json_patch_schema = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'version': '0.0.1',
    'title': 'ExtJsonPatchBase',
    'description': 'Stores an extended JSON Patch document',
    'type': 'object',
    'properties': {
        'sourceHashes': {
            'description': 'Mapping of aliases to source documents identiied by sha256 hexdigets',
            'type': 'object',
            'patternProperties': {
                _fieldname_regex: _cid_property('sha256 hexdigest of source document', optional=True),
            },
            'additionalProperties': False,
        },
        'target': _fieldname_property(),
        'operations': {
            'description': 'array of JSON patch operations',
            'type': 'array'
        }
    },
    'required': ['sourceHashes', 'target', 'operations'],
}
schema_list.append(ext_json_patch_schema)
