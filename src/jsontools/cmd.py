import os
import sys
from pathlib import Path
import argparse
from .storage import LocalJsonStorageProvider
from .version_control import JsonFileVersionControl



def action_track(filename, message, filevc):
    filename = Path(filename)
    node_hash = filevc.track(filename, message)
    print(f'Now tracking file {filename.name}.')
    print(f'Associated node hash: {node_hash}')
    sys.exit(0)


def action_istracked(filename, filevc): 
    filename = Path(filename)
    if filevc.is_tracked(filename):
        node_hashes = filevc.get_associated_node_hashes(filename)
        node_hashes_str = '\n, '.join(node_hashes)
        plsfx = 'es' if len(node_hashes) > 1 else ''
        print(
            f'The file {filename.name} is tracked and associated '
            f' with node hashes {plsfx}: {node_hashes_str}\n'
        )
    else:
        print('This file is not tracked')
        sys.exit(1)


def action_update(old_filename, new_filename, message, filevc):
    old_filename = Path(old_filename)
    filevc.update(old_filename, new_filename, message)
    print(f'Successfully registered update to json file {old_filename.name}')
    sys.exit(0)


def action_showlog(filename, filevc):
    messages = filevc.get_log(filename)
    print('\n'.join(messages))
    sys.exit(0)


def action_showdoc(short_hash, json_dumps_args, filevc):
    print(filevc.get_doc(short_hash, json_dumps_args))
    sys.exit(0)


def action_showdiff(old_short_hash, new_short_hash, filevc):
    print(filevc.get_diff(old_short_hash, new_short_hash))
    sys.exit(0)


def _prepare_parser():
    parser = argparse.ArgumentParser(description="Command line tool for tracking JSON files")

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    track_parser = subparsers.add_parser('track', help='Track a json file')
    track_parser.add_argument('filename', type=str, help='The json file to track') 
    track_parser.add_argument('-m', '--message', type=str, nargs='?', help='Optional message') 

    istracked_parser = subparsers.add_parser('istracked', help='Show if a json file is tracked')
    istracked_parser.add_argument('filename', type=str, help='The file whose track status is desired')

    update_parser = subparsers.add_parser('update', help='Update a json file')
    update_parser.add_argument('old_filename', type=str, help='The current tracked file')
    update_parser.add_argument('new_filename', type=str, help='The new file to replace it with')
    update_parser.add_argument('-m', '--message', type=str, nargs='?', help='Optional message') 

    showlog_parser = subparsers.add_parser('showlog', help='Show history of a file')
    showlog_parser.add_argument('filename', type=str, help='Filename whose history is desired')

    showdoc_parser = subparsers.add_parser('showdoc', help='Print json object on stdout')
    showdoc_parser.add_argument('short_hash', type=str, help='Short-form hash of file')
    showdoc_parser.add_argument('--indent', type=int, nargs='?', help='Indent for JSON output formatting')

    showdiff_parser = subparsers.add_parser('showdiff', help='Print diff to previous json object on stdout')
    showdiff_parser.add_argument('old_short_hash', type=str, help='Short-form hash of old file')
    showdiff_parser.add_argument('new_short_hash', type=str, help='Short-form hash of new file')
    return parser


def _perform_action(args, filevc):
    if args.command == 'track':
        action_track(args.filename, args.message, filevc)
    elif args.command == 'istracked':
        action_istracked(args.filename, filevc)
    elif args.command == 'update':
        action_update(args.old_filename, args.new_filename, args.message, filevc)
    elif args.command == 'showlog':
        action_showlog(args.filename, filevc)
    elif args.command == 'showdoc':
        json_dumps_args = {'indent': args.indent}
        action_showdoc(args.short_hash, json_dumps_args, filevc)
    elif args.command == 'showdiff':
        json_dumps_args = {'indent': args.indent}
        action_showdiff(
            args.old_short_hash, args.new_short_hash, json_dumps_args, filevc
        )
    else:
        print('Unknown command. Useh --help for usage.')


def _setup_storage_provider():
    if 'JSON_STORAGE_PATH' not in os.environ:
        raise TypeError(
            'Please define environment variable JSON_STORAGE_PATH '
            'with the path to the JSON document storage'
        )
    storage_path = Path(os.environ['JSON_STORAGE_PATH'])
    if not storage_path.is_dir():
        raise TypeError(
            'Please ensure that JSON_STORAGE_PATH points to '
            'an existing and writable directory on your computer'
        )
    return LocalJsonStorageProvider(storage_path)


if __name__ == '__main__':
    store = _setup_storage_provider() 
    filevc = JsonFileVersionControl(store)

    parser = _prepare_parser()
    args = parser.parse_args()
    _perform_action(args, filevc)
