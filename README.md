### jsonvc - Version Control for JSON Files

[![PyPI - Version](https://img.shields.io/pypi/v/jsontools.svg)](https://pypi.org/project/jsontools)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jsontools.svg)](https://pypi.org/project/jsontools)

-----

**This project is work in progress**

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

```console
git clone https://github.com/CodeVisionaries/jsonvc.git
pip install ./jsonvc
```

## Example

Change into the `examples/` directory. Here are example instructions for Linux and MacOs:

```console
mkdir json_storage
export JSON_STORAGE_PATH="$(pwd)/json_storage"

python -m jsonvc.cmd istracked first.json
python -m jsonvc.cmd track first.json -m 'first version'
python -m jsonvc.cmd update first.json second.json -m 'modify json file'
python -m jsonvc.cmd istracked first.json
python -m jsonvc.cmd showlog first.json
python -m jsonvc.cmd showlog second.json
python -m jsonvc.cmd showdiff 2388597
```


## License

`jsonvc` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
