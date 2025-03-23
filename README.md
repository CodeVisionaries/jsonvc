# jsontools

[![PyPI - Version](https://img.shields.io/pypi/v/jsontools.svg)](https://pypi.org/project/jsontools)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jsontools.svg)](https://pypi.org/project/jsontools)

-----

**This project is work in progress**

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install jsontools
```

## Example

Change into the `examples/` directory. Here are example instructions for Linux and MacOs:

```console
mkdir json_storage
export JSON_STORAGE_PATH="$(pwd)/json_storage"

python -m jsontools.cmd istracked first.json
python -m jsontools.cmd track first.json -m 'first version'
python -m jsontools.cmd update first.json second.json -m 'modify json file'
python -m jsontools.cmd istracked first.json
python -m jsontools.cmd showlog first.json
python -m jsontools.cmd showlog second.json
python -m jsontools.cmd showdiff 2388597
```


## License

`jsontools` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
