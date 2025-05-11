import os
import sys
import orjson
from pathlib import Path
import argparse
from .checksum import get_unique_json_repr
from .storage import LocalJsonStorageProvider
from .ipfs_storage import IpfsJsonStorageProvider
from .version_control import JsonFileVersionControl
from .custom_exceptions import (
    DocAlreadyTrackedError,
    SeveralNodesWithDocError,
)
from platformdirs import user_config_dir


APP_NAME = 'jsonvc'
CONFIG_FILENAME = 'config.json'
CACHE_FILENAME = 'cache.json'


def get_config_dir():
    config_dir = user_config_dir(APP_NAME)
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_filepath():
    config_dir = get_config_dir()
    return os.path.join(config_dir, CONFIG_FILENAME)


def read_config_file():
    config_path = get_config_filepath()
    if not os.path.isfile(config_path):
        return {}
    with open(config_path, 'r') as f:
        return orjson.loads(f.read())


def write_config_file(config_dict):
    config_path = get_config_filepath()
    with open(config_path, 'wb') as f:
        f.write(orjson.dumps(config_dict, option=orjson.OPT_INDENT_2))


def update_config_file(config_update):
    config = read_config_file()
    config.update(config_update)
    write_config_file(config)


def get_cache_filepath():
    config_dir = get_config_dir()
    return os.path.join(config_dir, CACHE_FILENAME)


def read_cache_file():
    cache_path = get_cache_filepath()
    if not os.path.isfile(cache_path):
        return {
            'known_nodes': {},
            'known_docs': {},
        }
    else:
        with open(cache_path, 'r') as f:
            return orjson.loads(f.read())


def write_cache_file(cache_dict):
    cache_path = get_cache_filepath()
    jsonstr = get_unique_json_repr(cache_dict)
    with open(cache_path, 'w') as f:
        f.write(jsonstr)


def action_track(filename, message, filevc):
    filename = Path(filename)
    node_hash = filevc.track(filename, message)
    write_cache_file(filevc.get_cache().to_dict())
    print(f'Now tracking file {filename.name}.')
    print(f'Associated node hash: {node_hash}')
    sys.exit(0)


def action_istracked(filename, filevc):
    filename = Path(filename)
    if filevc.is_tracked(filename):
        node_hashes = filevc.get_associated_node_hashes(filename)
        node_hashes_str = '\n'.join(node_hashes)
        plsfx = 'es' if len(node_hashes) > 1 else ''
        print(
            f'The file {filename.name} is tracked and associated '
            f'with node hash{plsfx}:\n{node_hashes_str}\n'
        )
    else:
        print(f'The file {filename.name} is not tracked')
        sys.exit(1)


def action_update(old_objref, new_objref, message, force, filevc):
    try:
        filevc.update(old_objref, new_objref, message, force)
        write_cache_file(filevc.get_cache().to_dict())
    except DocAlreadyTrackedError:
        print(
            'The new document is already in the system.\n'
            'Use the `showassoc` subcommand to list associated nodes.\n'
            'If you want to force the creation of a new node, use the --force flag'
        )
        sys.exit(1)
    except SeveralNodesWithDocError as exc:
        print('The reference to the object to be updated is ambiguous:\n')
        print('\n'.join(nh for nh in exc.node_hashes) + '\n')
        print('Please use a hash prefix instead of a filename to remove this ambiguity')
        sys.exit(1)

    print(f'Successfully registered update to json object {old_objref}')
    sys.exit(0)


def action_replace(target_file, update_file, message, force, targethash, filevc):
    try:
        filevc.replace(target_file, update_file, message, force, targethash)
        write_cache_file(filevc.get_cache().to_dict())
    except DocAlreadyTrackedError:
        print(
            f'The JSON document in {update_file.name} is already in the system.\n'
            'Use the `showassoc` subcommand to list associated nodes.\n'
            'If you want to force the replacement and creation of a new node, use the --force flag'
        )
        sys.exit(1)
    except SeveralNodesWithDocError as exc:
        print(f'Several nodes exist with the JSON document in {target_file.name}:\n')
        print('\n'.join(nh for nh in exc.node_hashes) + '\n')
        print('Please specify the --targethash argument to eliminate this ambiguity')
        sys.exit(1)
    print(f'Successfully replaced json file {target_file.name} by {update_file.name} ')
    sys.exit(0)


def action_showassoc(objref, full_hash, filevc):
    assoc_node_hashes = filevc.get_associated_node_hashes(objref)
    if len(assoc_node_hashes) == 0:
        print('This referenced JSON document is not tracked.')
        sys.exit(1)
    print('The referencd JSON document is associated with the following nodes:')
    messages = filevc.get_messages(objref)
    for h, m in messages.items():
        sh = h if full_hash else h[:10]
        print(f'{sh}: {m}')


def action_showlog(objref, full_hash, filevc):
    try:
        log_info = filevc.get_linear_history(objref)
        for node in log_info:
            h = node.get_hash()
            short_hash = h if full_hash else h[:10]
            message = node.get_meta()['message']
            print(f'{short_hash}: {message}')

    except SeveralNodesWithDocError as exc:
        print('This JSON document is associated with several nodes:\n')
        print('\n'.join(exc.node_hashes) + '\n')
        print(
            'You can use `showassoc` to see the available nodes and '
            'use one of the hashes (or a hash prefix) to dispaly the '
            'particular history'
        )
        sys.exit(1)
    sys.exit(0)


def action_showdoc(short_hash, json_dumps_args, filevc):
    print(filevc.get_doc(short_hash, json_dumps_args))
    sys.exit(0)


def action_showdiff(old_short_hash, new_short_hash, json_dumps_args, filevc):
    print(filevc.get_diff(old_short_hash, new_short_hash, json_dumps_args))
    sys.exit(0)


def action_discover(node_hashes, filevc):
    discovered_nodes = filevc.get_cache().discover_nodes(node_hashes)
    write_cache_file(filevc.get_cache().to_dict())
    print('Discovered nodes:')
    print('\n'.join(discovered_nodes))
    sys.exit(0)


def action_config_showdir():
    print(get_config_dir())
    sys.exit(0)


def action_config_show():
    config = read_config_file()
    print(orjson.dumps(config, option=orjson.OPT_INDENT_2).decode('utf-8'))
    sys.exit(0)


def action_config_set(key, value):
    allowed_keys = (
        'storage-backend',
        'local-storage-path',
        'ipfs-gateway-url',
        'ipfs-rpc-url',
        'ipfs-rpc-url-upload',
        'ipfs-cache-dir',
    )
    if key not in allowed_keys:
        print(f'key must be in ({", ".join(allowed_keys)})')
        sys.exit(1)
    if key == 'storage-backend':
        allowed_values = ('local', 'ipfs')
        if value not in allowed_values:
            print(f'value must be in ({", ".join(allowed_values)})')
            sys.exit(1)
    update_config_file({key: value})


def _add_json_dumps_args(parser):
    parser.add_argument('--indent', action='store_true', help='Enable indent for JSON output formatting')


def _add_message_arg(parser):
    parser.add_argument('-m', '--message', type=str, required=True, help='The commit message')


def _prepare_parser():
    parser = argparse.ArgumentParser(description="Command line tool for tracking JSON files")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable developer debug output')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    track_parser = subparsers.add_parser('track', help='Track a json file')
    track_parser.add_argument('filename', type=str, help='The json file to track')
    track_parser.add_argument('--provide', action='store_true', help='Provide file to peers (IPFS only)')
    _add_message_arg(track_parser)

    istracked_parser = subparsers.add_parser('istracked', help='Show if a json file is tracked')
    istracked_parser.add_argument('filename', type=str, help='The file whose track status is desired')

    update_parser = subparsers.add_parser('update', help='Update a json file')
    update_parser.add_argument('old_objref', type=str, help='The current tracked JSON document')
    update_parser.add_argument('new_objref', type=str, help='The new JSON document to replace it with')
    update_parser.add_argument('--force', action='store_true', help='Force creation of node')
    update_parser.add_argument('--provide', action='store_true', help='Provide file to peers (IPFS only)')
    _add_message_arg(update_parser)

    replace_parser = subparsers.add_parser('replace', help='Update target file and remove source file')
    replace_parser.add_argument('target_file', type=Path, help='The file to be updated')
    replace_parser.add_argument('update_file', type=Path, help='The file with the updatd JSON (will be deleted)')
    replace_parser.add_argument('--force', action='store_true', help='Force replacement even if JSON document in update_file already tracked')
    replace_parser.add_argument('--targethash', type=str, nargs='?',  help='Target node hash to eliminate ambiguity')
    replace_parser.add_argument('--provide', action='store_true', help='Provide file to peers (IPFS only)')
    _add_message_arg(replace_parser)

    showassoc_parser = subparsers.add_parser('showassoc', help='Show nodes associated with JSON document')
    showassoc_parser.add_argument('--full-hash', action='store_true', help='Show full hash in output')
    showassoc_parser.add_argument('objref', type=str, help='JSON document reference')

    showlog_parser = subparsers.add_parser('showlog', help='Show history of a file')
    showlog_parser.add_argument('--full-hash', action='store_true', help='Show full hash in output')
    showlog_parser.add_argument('objref', type=str, help='JSON document whose history is desired')

    showdoc_parser = subparsers.add_parser('showdoc', help='Print json object on stdout')
    showdoc_parser.add_argument('objref', type=str, help='JSON document reference')
    _add_json_dumps_args(showdoc_parser)

    showdiff_parser = subparsers.add_parser('showdiff', help='Print diff to previous json object on stdout')
    showdiff_parser.add_argument('old_objref', type=str, help='Short-form hash of old file')
    showdiff_parser.add_argument('new_objref', type=str, help='Short-form hash of new file')
    _add_json_dumps_args(showdiff_parser)

    discover_parser = subparsers.add_parser('discover', help='Discover tracking nodes starting from seed nodes')
    discover_parser.add_argument('node_hashes', nargs='+', help='List with seed node hashes')

    _prepare_config_subparser(subparsers)
    return parser


def _prepare_config_subparser(subparsers):
    config_parser = subparsers.add_parser('config', help='Management of configuration file')
    subparsers = config_parser.add_subparsers(dest='config_command', help='Available commands')
    subparsers.add_parser('showdir', help='Show configuration directory')
    subparsers.add_parser('show', help='Show the configuration')
    set_parser = subparsers.add_parser('set', help='Set configuration variable')
    set_parser.add_argument('key', help='variable name')
    set_parser.add_argument('value', help='value')


def _setup_local_storage_provider(config):
    if 'JSON_STORAGE_PATH' not in os.environ:
        storage_path = config.get('local-storage-path', None)
        if storage_path is None:
            print(
                'Please define environment variable JSON_STORAGE_PATH '
                'with the path to the JSON document storage or set the '
                '`local-storage-path` variable in the configuration'
            )
            sys.exit(1)
    else:
        storage_path = os.environ['JSON_STORAGE_PATH']

    storage_path = Path(storage_path)
    if not storage_path.is_dir():
        print(
            f'The directory `{storage_path}` to store JSON objects '
            'does not exist. Either create it or set the environment variable '
            '`JSON_STORAGE_PATH` to point to an existing directory or '
            'set the `local-storage-path` variable in the configuration'
        )
        sys.exit(1)
    return LocalJsonStorageProvider(storage_path)


def _setup_ipfs_storage_provider(config):
    req_vars = ('ipfs-cache-dir', 'ipfs-gateway-url', 'ipfs-rpc-url')
    var_missing = False
    for v in req_vars:
        if v not in config:
            var_missing = True
            print(f'Please set variable `{v}` in configuration')
    if var_missing:
        sys.exit(1)
    ipfs_rpc_url_upload = config.get('ipfs-rpc-url-upload', None)
    return IpfsJsonStorageProvider(
        *(config[v] for v in req_vars),
        rpc_api_url_upload=ipfs_rpc_url_upload
    )


def _setup_storage_provider():
    config = read_config_file()
    if config['storage-backend'] == 'local':
        return _setup_local_storage_provider(config)
    elif config['storage-backend'] == 'ipfs':
        return _setup_ipfs_storage_provider(config)


def _perform_config_action(args):
    if args.config_command == 'showdir':
        action_config_showdir()
    elif args.config_command == 'show':
        action_config_show()
    elif args.config_command == 'set':
        action_config_set(args.key, args.value)
    else:
        print('Unknown config command. Use --help for usage')
    return


def _perform_regular_action(args, filevc):
    activate_provie = lambda: None
    if hasattr(args, 'provide') and args.provide:
        storeprov = filevc.get_storage_provider()
        if isinstance(storeprov, IpfsJsonStorageProvider):
            storeprov.enable_provide()

    if args.command == 'track':
        action_track(args.filename, args.message, filevc)
    elif args.command == 'istracked':
        action_istracked(args.filename, filevc)
    elif args.command == 'update':
        action_update(args.old_objref, args.new_objref, args.message, args.force, filevc)
    elif args.command == 'replace':
        action_replace(args.target_file, args.update_file, args.message, args.force, args.targethash, filevc)
    elif args.command == 'showassoc':
        action_showassoc(args.objref, args.full_hash, filevc)
    elif args.command == 'showlog':
        action_showlog(args.objref, args.full_hash, filevc)
    elif args.command == 'showdoc':
        json_dumps_args = {'indent': args.indent}
        action_showdoc(args.objref, json_dumps_args, filevc)
    elif args.command == 'showdiff':
        json_dumps_args = {'indent': args.indent}
        action_showdiff(
            args.old_objref, args.new_objref, json_dumps_args, filevc
        )
    elif args.command == 'discover':
        action_discover(args.node_hashes, filevc)
    else:
        print('Unknown command. Use --help for usage.')


def _perform_action(args):
    if args.command == 'config':
        return _perform_config_action(args)

    cache_dict = read_cache_file()
    store = _setup_storage_provider()
    filevc = JsonFileVersionControl(store)
    filevc.get_cache().from_dict(cache_dict)

    _perform_regular_action(args, filevc)


def main():
    parser = _prepare_parser()
    args = parser.parse_args()
    if not args.debug:
        try:
            _perform_action(args)
        except Exception as e:
            print(str(e))
            sys.exit(1)
    else:
        _perform_action(args)


if __name__ == '__main__':
    main()
