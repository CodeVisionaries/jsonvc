### jsonvc - Version Control for JSON Files

[![PyPI - Version](https://img.shields.io/pypi/v/jsontools.svg)](https://pypi.org/project/jsontools)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jsontools.svg)](https://pypi.org/project/jsontools)

-----

This `jsonvc` Python package is a prototype for data model-agnostic version tracking
based on [JSON files](https://www.json.org/json-en.html). Data model-agnostic means
that the evolution of any JSON file can be tracked irrespective of how the
basic building blocks of the JSON format (object, array, number, string) are
combined to represent specific information. By extension, this also means that
the tool is agnostic to the type of data stored in a JSON file,
e.g. experimental nuclear data, integral benchmark data, nuclear model predictions).

The tool comes with a command-line interface that can be invoked via the
`jsonvc` command and its usage is explained below.

The basic approach to version tracking relies on linking documents together
by using a content-derived name (cryptographic hash). Together with the
design choice that all data are stored as JSON documents, this represents
a very general design approach that is compatible with many established
database products and technologies. In principle, it does not matter whether
the JSON documents are stored in, e.g., a
[CouchDB](https://couchdb.apache.org/),
[MongoDB](https://www.mongodb.com/),
the [Interplanetary File System (IPFS)](https://ipfs.tech/)
or simply in a local directory under their content-derived names.

This prototype supports for the time being the storage of JSON 
documents in a local directory under content-derived filenames
as well as on IPFS for truly decentralized data storage,
which facilitates building on the work of others in a globally
traceable way.

## Table of Contents

- [Installation](#installation)
- [Use with local storage](#use-with-local-storage)
- [Use with IPFS](#use-with-interplanetary-file-system)
- [License](#license)

## Installation

The installation into a dedicated virtual environtment
is recommended. To create it:
```console
python -m venv venv
```
The environment can be activated by
```console
source venv/bin/activate  # Linux, MacOS
docenv\Scripts\activate.bat  # Windows  
```
and deactivated by
```console
deactivate
```

Activate the created environemnt (recommended but not required)
and then run:
```console
pip install git+https://github.com/codevisionaries/jsonvc.git
```

For running the example instructions below as they are,
also clone the repository to make the example JSON files in
the `jsonvc/examples` directory locally available.
```console
git clone git+https://github.com/codevisionaries/jsonvc.git
```

## Use with local storage 

This is the recommended approach to dabble with the
prototype and get a feeling for its use. 
First, configure the use of the local storage backend.
On the command line, run:
```console
jsonvc config set storage-backend local
jsonvc config set local-storage-path <absolute-path-to-empty-directory>
```
The `<absolute-path-to-empty-directory>` should refer to an existing
and empty directory. It will be filled with JSON files stored under
using their SHA-256 checksum as name.

You can also view the location of the configuration directory:
```console
jsonvc config showdir
```
The configuration variables can be shown by invoking:
```console
jsonvc config show
```

After the successful setup, you can use the `jsonvc` tool to
track the evolution of JSON files over time. A design feature
is that the tool does not care about the storage location or the
name of a JSON file. It will recognize based on the content
whether this file has been encountered before is being tracked.

Here is a simple example invocation that walks you through some
of the available commands. Before executing them,
change into the `jsonvc/examples/` directory (assuming you have
cloned the repository above as described above).

```console
jsonvc istracked first.json
jsonvc track first.json -m "first version"
jsonvc update first.json second.json -m "modify json file"
jsonvc istracked first.json
jsonvc showlog first.json
# The showlog command will determine based on file-content
# whether the file is known and print the sequence of updates.
# So the tracking is agnostic to where the files are stored.
# and they can be moved around on a whim.
jsonvc showlog second.json
# different ways to compare historic versions
# output is in JSON Patch format (RFC 6901)
jsonvc showdiff fc166 cbea64
# historic versions can also be compared with existing files
jsonvc showdiff fc166 second.json
# or directly compare files  
jsonvc showdiff first.json second.json
```

## Use with Interplanetary File System

If you quickly want to try out the `jsonvc` prototype,
it is highly recommended to use a local storage directory
(see previous section). The setup to use the IPFS as
backend is more involved.

The `jsonvc` tool interacts with IPFS via an
[IPFS gateways](https://docs.ipfs.tech/concepts/ipfs-gateway/)
for data retrieval and an
[IPFS RPC API](https://docs.ipfs.tech/reference/kubo/rpc/) endpoint
for making data globally available.

You can [install the IPFS Kubo client](https://docs.ipfs.tech/install/command-line/) locally.
Once done, start it from the command line:
```console
ipfs daemon
```
By default, the IPFS dameon will provide an IPFS gateway at
`http://localhost:8080/` and an IPFS RPC endpoint at
`http://localhost:5001`. Assuming these defaults,
configure `jsonvc` like this:
```console
jsonvc config set storage-backend ipfs
jsonvc config set ipfs-gateway-url http://localhost:8080/
jsonvc config set ipfs-rpc-url http://localhost:5001/api/
jsonvc config set ipfs-cache-dr <absolute-path-to-empty-dir>
```
The directory associated with `ipfs-cache-dir` is used to cache files
stored on and retrieved from the IPFS for faster access.
Please note that it is also possible to rely on a public
[jailed IPFS RPC API](https://github.com/CodeVisionaries/ipfs-flask-reverse-proxy) endpoint.
We have such an endpoint set up for collaborators. If you are interested
to contribute to this project by testing it or code development, please reach out to us.

After this setup, you can use exactly the same commands as above.
The only IPFS related particularity is that the propagation of file information
through the decentralized network may take a bit (minutes or hours, depending on
the hardware resources and load of the IPFS node). To accelerate this process
to seconds, you can use the provide flag with commands associated with
uploading files,namely:
```console
jsonvc track first.json -m "test upload" --provide
jsonvc update first.json second.json -m "modify json file" --provide
```

With this extra option, the execution of these commands will take
longer but you hae a stronger guarantee that the files will likely
be immediatley discoverable by other IPFS participants afterwards.


## License

`jsonvc` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
