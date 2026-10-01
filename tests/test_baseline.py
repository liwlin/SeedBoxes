"""Clean-install and upstream SVG baselines: no GUI or patched engine required."""
from pathlib import Path
import xml.etree.ElementTree as ET

import tomli

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '9d93cd81b05d6ef5b0f3d4b4d6ed7eaf5bbed0dd'


def test_lock_has_no_local_boxes_source():
    lock = tomli.loads((ROOT / 'uv.lock').read_text())
    package = next(p for p in lock['package'] if p['name'] == 'boxes')
    assert 'editable' not in package['source'], 'Boxes.py still depends on an old local checkout'
    assert COMMIT in package['source']['git']


def test_closedbox_baseline_renders():
    from boxes.generators.closedbox import ClosedBox
    box = ClosedBox()
    box.parseArgs(['--x', '120', '--y', '80', '--h', '60', '--thickness', '3',
                   '--burn', '0', '--format', 'svg', '--reference', '0',
                   '--labels', '0', '--qr_code', '0'])
    box.open()
    box.render()
    root = ET.fromstring(box.close().getvalue())
    assert root.tag.endswith('svg')
    assert root.attrib['width'].endswith('mm')
    assert root.attrib['height'].endswith('mm')
    assert len(root.findall('{http://www.w3.org/2000/svg}g')) == 6


def test_manifest_reports_actual_engine():
    from scripts.verify_baseline import collect_manifest
    manifest = collect_manifest()
    assert manifest['engineCommit'] == COMMIT
    assert manifest['pythonVersion'].startswith('3.10.')
    assert manifest['discoveredGenerators'] > 0
    assert 'svg' in manifest['supportedFormats']


def test_saved_svg_baselines_match():
    import json
    from scripts.verify_baseline import svg_summary
    for name in ('ClosedBox', 'ABox'):
        expected = json.loads((ROOT / 'tests/fixtures/baseline' / (name + '.json')).read_text())
        assert svg_summary(name) == expected


def test_legacy_backend_still_renders():
    from backend import Api
    api = Api()
    assert api.ping()['status'] == 'ok'
    assert api.list_groups()
    result = api.preview('ClosedBox', {'x': 120, 'y': 80, 'h': 60})
    assert 'svg' in result, result
