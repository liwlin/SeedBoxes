"""JSON-facing dataclasses use the documented field names verbatim."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Project:
    schemaVersion: int
    projectId: str
    revision: int
    name: str
    units: str
    engine: dict[str, Any]
    adapter: dict[str, Any]
    generatorId: str
    parameters: dict[str, Any]
    profileSnapshot: dict[str, Any]
    features: list[dict[str, Any]]
    layout: dict[str, Any]
    validationPolicy: dict[str, Any]
    calibrationRef: dict[str, Any] | None
    trialRecords: list[dict[str, Any]]
    createdAt: str
    updatedAt: str
    viewState: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Path2D:
    pathId: str
    commands: tuple[tuple, ...]
    closed: bool
    operation: str


@dataclass(frozen=True)
class PanelGeometry:
    outer: Path2D
    holes: tuple[Path2D, ...] = ()
    engravings: tuple[Path2D, ...] = ()


@dataclass(frozen=True)
class CapturedPanel:
    panelId: str
    displayCode: str
    sourceRole: str
    thicknessMm: float
    widthMm: float
    heightMm: float
    geometry: PanelGeometry
    canvasToLocal: tuple[float, ...]
    edgeTypes: tuple[str, ...]
    assemblyTransform: tuple[float, ...]
    # Captured closed-box edge identities, not a claim of assembly-path validation.
    jointDescriptors: tuple[dict, ...] = ()


@dataclass(frozen=True)
class CapturedModel:
    mode: str
    projectId: str
    revision: int
    panels: tuple[CapturedPanel, ...]
    engineFingerprint: dict[str, Any]
    innerDimensions: dict[str, float]
    diagnostics: tuple[dict, ...] = ()


@dataclass(frozen=True)
class Panel:
    panelId: str
    displayCode: str
    label: str
    thicknessMm: float
    nominalGeometry: PanelGeometry
    cutGeometry: dict[str, Any]
    localFrame: dict[str, Any]
    assemblyTransform: dict[str, Any]
    layoutTransform: dict[str, Any] | None
    joints: tuple[dict, ...]
    provenance: dict[str, Any]


@dataclass(frozen=True)
class GeneratedModel:
    generationId: str
    projectId: str
    revision: int
    inputHash: str
    engineFingerprint: dict[str, Any]
    adapterVersion: str
    units: str
    panels: tuple[Panel, ...]
    sheets: tuple[dict, ...]
    diagnostics: tuple[dict, ...]
    generatedAt: str
    geometries: dict[str, bool]
    innerDimensions: dict[str, float]


@dataclass(frozen=True)
class ProcessProfile:
    schemaVersion: int
    profileId: str
    version: int
    name: str
    status: str
    machine: dict[str, Any]
    material: dict[str, Any]
    process: dict[str, Any]
    compensation: dict[str, Any]
    machineBed: dict[str, Any]
    rules: dict[str, Any]
    evidence: dict[str, Any]
