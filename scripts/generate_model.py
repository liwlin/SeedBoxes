"""Inspect structured geometry without launching the desktop UI.

uv run --locked python scripts/generate_model.py tests/fixtures/project.json --output /tmp/model.json
The output is a diagnostic snapshot, not a manufacturing export.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seedboxes.domain.serialization import normalize_project, to_json
from seedboxes.engine.geometry_service import GeometryService


def main():
    parser = argparse.ArgumentParser(description='SeedBoxes structured geometry diagnostic')
    parser.add_argument('project', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    model = GeometryService().generate(normalize_project(json.loads(args.project.read_text(encoding='utf-8'))))
    result = json.dumps(to_json(model),ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.write_text(result,encoding='utf-8')
        print(f'SeedBoxes: {len(model.panels)} panels; manufacturing checks NOT performed; {args.output}')
    else:
        print(result,end='')


if __name__ == '__main__':
    main()
