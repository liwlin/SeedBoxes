import copy
import importlib
import json
from pathlib import Path

import pytest
from seedboxes.domain.serialization import normalize_project, to_json, validate_contract
from seedboxes.engine.paths import path_bounds

ROOT=Path(__file__).resolve().parents[1]


def service(**kwargs):
    try:
        return importlib.import_module('seedboxes.engine.geometry_service').GeometryService(**kwargs)
    except ImportError:
        pytest.fail('Dual-channel geometry service has not been implemented')


def data():
    return json.loads((ROOT/'tests/fixtures/project.json').read_text())


def with_hole(d=None, kind='circleHole'):
    d=d or data()
    d['features']=[{'featureId':'hole-1','panelId':'front','kind':kind,'operation':'cut',
                   'anchor':{'mode':'absolute','xMm':30,'yMm':25},
                   'parameters':{'diameterMm':8} if kind=='circleHole' else {'widthMm':12,'heightMm':8},
                   'rotationDeg':0,'enabled':True}]
    return d


def test_burn_changes_toolpath_not_nominal():
    s=service();d=data();a=s.generate(normalize_project(d))
    d['profileSnapshot']['compensation']['boxesBurnMm']=0.2
    b=s.generate(normalize_project(d))
    assert [p.nominalGeometry for p in a.panels]==[p.nominalGeometry for p in b.panels]
    assert a.panels[0].cutGeometry!=b.panels[0].cutGeometry
    assert path_bounds(a.panels[0].cutGeometry['operations'][0])==pytest.approx((-3.1,-3.1,123.1,63.1),abs=1e-8)
    assert path_bounds(b.panels[0].cutGeometry['operations'][0])==pytest.approx((-3.2,-3.2,123.2,63.2),abs=1e-8)
    assert a.inputHash!=b.inputHash


def test_layout_shift_does_not_change_local_geometry():
    s=service();d=data();a=s.generate(normalize_project(d))
    d['layout']['gapMm']=9;d['layout']['sheetWidthMm']=900
    b=s.generate(normalize_project(d))
    assert [p.nominalGeometry for p in a.panels]==[p.nominalGeometry for p in b.panels]
    assert a.inputHash!=b.inputHash


def test_inside_outside_equivalence():
    s=service();d=data();a=s.generate(normalize_project(d))
    d['parameters'].update(x=126,y=86,h=66,outside=True)
    b=s.generate(normalize_project(d))
    assert a.innerDimensions==b.innerDimensions
    assert [p.nominalGeometry for p in a.panels]==[p.nominalGeometry for p in b.panels]
    assert [p.assemblyTransform for p in a.panels]==[p.assemblyTransform for p in b.panels]


@pytest.mark.parametrize('kind',['circleHole','rectHole'])
def test_hole_compensated_once(kind):
    model=service().generate(normalize_project(with_hole(kind=kind)))
    front=model.panels[0]
    nominal=front.nominalGeometry.holes[0]
    tool=front.cutGeometry['operations'][1]
    expected=(26,21,34,29) if kind=='circleHole' else (24,21,36,29)
    # Upstream cubic circle approximation has a ~2.4e-6 mm extrema error here.
    assert path_bounds(nominal)==pytest.approx(expected,abs=1e-5)
    assert path_bounds(tool)==pytest.approx((expected[0]+.1,expected[1]+.1,expected[2]-.1,expected[3]-.1),abs=1e-5)
    assert nominal.pathId==tool.pathId=='front:feature:hole-1'
    assert tool.operation=='cut_inner'
    assert all(not p.nominalGeometry.holes for p in model.panels[1:])


def test_generated_model_matches_schema():
    model=service().generate(normalize_project(with_hole()))
    validate_contract('generated-model',to_json(model))
    assert model.sheets==()
    assert all(p.layoutTransform is None for p in model.panels)
    assert any(d['code']=='MANUFACTURING_UNCHECKED' for d in model.diagnostics)


def test_cache_evicts_oldest_and_detaches_results():
    s=service(max_entries=2);p=normalize_project(data())
    a=s.generate(p);b=s.generate(p)
    a.panels[0].cutGeometry['operations']=()
    assert s.get_generation(a.generationId).panels[0].cutGeometry['operations']
    s.get_generation(a.generationId)
    c=s.generate(p)
    with pytest.raises(KeyError):s.get_generation(b.generationId)
    assert s.get_generation(c.generationId).inputHash==c.inputHash


def test_cache_rejects_oversize_result():
    with pytest.raises(ValueError,match='缓存|cache'):
        service(max_bytes=100).generate(normalize_project(data()))


def test_project_snapshot_not_mutated():
    s=service();p=normalize_project(with_hole());before=to_json(p)
    s.generate(p)
    assert to_json(p)==before


@pytest.mark.parametrize('change',[{'rotationDeg':45},{'parameters':{'diameterMm':.1}}])
def test_unsupported_feature_is_not_silently_ignored(change):
    s=service();d=with_hole();d['features'][0].update(change)
    with pytest.raises(ValueError):s.generate(normalize_project(d))


def test_disabled_feature_does_not_generate_hole():
    d=with_hole();d['features'][0]['enabled']=False
    model=service().generate(normalize_project(d))
    assert not model.panels[0].nominalGeometry.holes


def test_structured_backend_api_and_legacy_coexist():
    from backend import Api
    api=Api()
    assert hasattr(api,'generate_model'), 'Backend does not yet expose structured geometry'
    result=api.generate_model(with_hole())
    assert result['ok'],result
    validate_contract('generated-model',result['data'])
    assert 'svg' in api.preview('ClosedBox',{'x':120,'y':80,'h':60})
    assert not api.generate_model({'schemaVersion':99})['ok']


@pytest.mark.parametrize('commands',[[['BOGUS'],['C','x']],[['M',0,0],['L',1]],[['M',0,0],['Z',1]],[['M',0,0],['C',1,2,3,4,5,'bad']]])
def test_generated_contract_rejects_malformed_commands(commands):
    payload=to_json(service().generate(normalize_project(data())))
    payload['panels'][0]['nominalGeometry']['outer']['commands']=commands
    with pytest.raises(ValueError):
        validate_contract('generated-model',payload)
