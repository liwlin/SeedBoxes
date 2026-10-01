"""Version gate: preserve future documents verbatim; never guess a migration."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import math

from seedboxes.domain.serialization import normalize_project

CURRENT_SCHEMA = 1


@dataclass(frozen=True)
class ReadOnlyProject:
    document: dict
    sourcePath: str
    readOnly: bool = True


def load_document(data: dict, path: Path):
    version = data.get('schemaVersion')
    if type(version) not in (int,float) or not math.isfinite(version) or version < 1 or int(version) != version:
        raise ValueError('工程 schemaVersion 无效')
    if version > CURRENT_SCHEMA:
        return ReadOnlyProject(deepcopy(data),str(path))
    return normalize_project(data)
