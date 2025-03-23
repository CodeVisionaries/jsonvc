import re
import json
from typing import Optional, List
from pathlib import Path
import subprocess

if __name__ != '__main__':
    # if invoked as a module
    from .schemas import schema_list
else:
    # if run directly 
    from schemas import schema_list


def _load_json_file(filename: Path) -> dict:
    with open(filename, 'r') as f:
        cont = f.read()
    return json.loads(cont)


def _camel_to_snake(camel_str):
    """Convert strings from CamelCase to snake_case."""
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', camel_str).lower()

def _normalize_version_str(versionstr):
    return 'v' + versionstr.replace('.', '_')


def _fix_python_model_file(filename):
    """Replace argument name `regex` by `pattern` for pydantic v2"""
    with open(filename, 'r') as f:
        cont = f.read()
    cont = cont.replace('regex=', 'pattern=')
    with open(filename, 'w') as f:
        f.write(cont)


def generate_json_schema_files(json_schemas: list, schema_dir: Path) -> dict:
    schema_files = []
    for js in json_schemas:
        schema_name = js['title']
        schema_name_snake = _camel_to_snake(schema_name)
        schema_version = _normalize_version_str(js['version'])
        schema_filename = f'schema_{schema_name_snake}_{schema_version}.json'
        schema_filepath = Path(schema_dir) / schema_filename
        schema_json = json.dumps(js, indent=2)
        with open(schema_filepath, 'w') as f:
            f.write(schema_json)
        print (f'generated {schema_filename} from {schema_name} schema')
        schema_files.append(schema_filename)


def generate_python_data_models(model_dir: Path, schema_dir: Path, schema_files: Optional[List[str]] = None):
    schema_dir = Path(schema_dir)
    model_dir = Path(model_dir)
    if schema_files is None:
        file_iter = schema_dir.iterdir()
        schema_files = [p for p in file_iter if p.is_file() and p.suffix == '.json']
    else:
        schema_files = [Path(p) for p in schema_files]

    import_list = []
    for schema_file in schema_files:
        fp = schema_dir / schema_file
        json_schema = _load_json_file(fp)
        schema_name = json_schema['title']
        schema_name_snake = _camel_to_snake(schema_name)
        python_model_filename = schema_name_snake + '.py'
        python_model_filepath = model_dir / python_model_filename 
        subprocess.run([
            'datamodel-codegen',
            '--input-file-type', 'jsonschema',
            '--input', schema_file,
            '--output', python_model_filepath,
            '--output-model-type', 'pydantic_v2.BaseModel',
        ])
        # _fix_python_model_file(python_model_filepath)
        print(f'generated {python_model_filename} with {schema_name} model class')
        import_list.append((schema_name_snake, schema_name))

    with open(model_dir / '__init__.py', 'w') as f:
        for module_name, schema_name in import_list:
            f.write(f'from .{module_name} import {schema_name}\n')


if __name__ == '__main__':
    current_script_dir = Path(__file__).parent
    json_package_path = current_script_dir.resolve() 
    schema_dir = json_package_path / 'schemas'
    model_dir = json_package_path / 'base_models'
    generate_json_schema_files(schema_list, schema_dir)
    generate_python_data_models(model_dir, schema_dir)
