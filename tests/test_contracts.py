import copy
import importlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def api():
    try:
        return importlib.import_module('seedboxes.domain.serialization')
    except ImportError:
        pytest.fail('Project serialization contract has not been implemented')


@pytest.fixture
def project_data():
    return json.loads((ROOT / 'tests/fixtures/project.json').read_text())


def test_project_round_trip(project_data):
    s = api()
    project = s.normalize_project(project_data)
    assert s.to_json(project) == project_data
    assert s.normalize_project(s.to_json(project)) == project


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_reject_nonfinite(project_data, bad):
    s = api()
    project_data['parameters']['x'] = bad
    with pytest.raises(ValueError, match='有限|finite'):
        s.normalize_project(project_data)


def test_view_state_does_not_change_input_hash(project_data):
    s = api()
    p = s.normalize_project(project_data)
    first = s.project_input_hash(p, p.engine)
    project_data.update(name='另一个名字', revision=23, updatedAt='2026-10-02T00:00:00Z')
    project_data['viewState'] = {'camera': [1, 2, 3]}
    assert s.project_input_hash(s.normalize_project(project_data), p.engine) == first


@pytest.mark.parametrize('field', ['profileSnapshot', 'features', 'layout', 'validationPolicy'])
def test_process_change_changes_hash(project_data, field):
    s = api()
    p = s.normalize_project(project_data)
    data = copy.deepcopy(project_data)
    if field == 'features':
        data[field] = [{'featureId': 'hole-1', 'panelId': 'front', 'kind': 'circleHole', 'operation': 'cut',
                        'anchor': {'mode': 'absolute', 'xMm': 30, 'yMm': 25},
                        'parameters': {'diameterMm': 8}, 'rotationDeg': 0, 'enabled': True}]
    elif field == 'profileSnapshot':
        data[field]['compensation']['boxesBurnMm'] = 0.2
    elif field == 'layout':
        data[field]['gapMm'] = 4
    else:
        data[field]['ruleSetVersion'] = '2.0.0'
    assert s.project_input_hash(s.normalize_project(data), p.engine) != s.project_input_hash(p, p.engine)


def test_equivalent_numeric_values_hash_identically(project_data):
    s = api()
    p = s.normalize_project(project_data)
    project_data['parameters']['x'] = 120.0
    project_data['profileSnapshot']['compensation']['jointClearanceMm'] = -0.0
    assert s.project_input_hash(s.normalize_project(project_data), p.engine) == s.project_input_hash(p, p.engine)


@pytest.mark.parametrize('change', [
    {'schemaVersion': 2}, {'units': 'inch'}, {'unknownField': 1}, {'revision': True},
    {'projectId': '../bad'}, {'name': ''}
])
def test_reject_invalid_contract(project_data, change):
    s = api()
    project_data.update(change)
    with pytest.raises(ValueError):
        s.normalize_project(project_data)


def test_input_mutation_does_not_mutate_project(project_data):
    s = api()
    p = s.normalize_project(project_data)
    project_data['parameters']['x'] = 500
    assert p.parameters['x'] == 120


def test_schema_matches_example(project_data):
    api()
    schema_path = ROOT / 'schemas/project.schema.json'
    assert schema_path.exists()
    validator = Draft202012Validator(json.loads(schema_path.read_text()), format_checker=Draft202012Validator.FORMAT_CHECKER)
    assert not list(validator.iter_errors(project_data))
