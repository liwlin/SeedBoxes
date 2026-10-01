"""Canonical JSON and boundary validation for manufacturing snapshots."""
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator

from .models import Project


def ensure_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('数值必须有限 (finite)')
    if value is None or type(value) in (str, bool, int, float):
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            ensure_json(item)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            ensure_json(item)
        return
    raise ValueError('项目只能包含 JSON 数据')


def to_json(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    ensure_json(value)
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


@lru_cache(maxsize=16)
def schema_validator(name: str) -> Draft202012Validator:
    if name not in {'project', 'generated-model', 'profile', 'issue', 'response'}:
        raise ValueError('未知数据契约')
    root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    schema = json.loads((root / 'schemas' / (name + '.schema.json')).read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def validate_contract(name: str, data: dict) -> None:
    ensure_json(data)
    error = next(schema_validator(name).iter_errors(data), None)
    if error:
        location = '.'.join(map(str, error.absolute_path)) or name
        raise ValueError(f'数据契约不匹配：{location}: {error.message}')


def normalize_project(data: dict) -> Project:
    data = deepcopy(data)
    validate_contract('project', data)
    ids = [f['featureId'] for f in data['features']]
    if len(ids) != len(set(ids)):
        raise ValueError('特征 ID 不能重复')
    return Project(**data)


def _canonical(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)  # 120 == 120.0 and 0 == -0.0
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    return value


def project_input_hash(project: Project, engine: dict) -> str:
    data = to_json(project)
    for key in ('projectId', 'revision', 'name', 'createdAt', 'updatedAt', 'viewState', 'trialRecords'):
        data.pop(key, None)
    data['engineFingerprint'] = {k: engine[k] for k in ('name', 'version', 'commit')}
    # Warning acknowledgements do not change the manufacturing definition.
    data['validationPolicy'].pop('acknowledgedIssueIds', None)
    normalized = _canonical(data)
    payload = json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
