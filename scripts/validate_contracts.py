"""Validate versioned schema documents and checked-in examples."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from seedboxes.domain.serialization import normalize_project, schema_validator, to_json


def main():
    for path in sorted((ROOT / 'schemas').glob('*.schema.json')):
        schema_validator(path.name.removesuffix('.schema.json'))
    example = json.loads((ROOT / 'tests/fixtures/project.json').read_text(encoding='utf-8'))
    assert to_json(normalize_project(example)) == example
    print('Schemas and project example validated')


if __name__ == '__main__':
    main()
