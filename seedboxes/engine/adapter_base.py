from typing import Literal, Protocol
from seedboxes.domain.models import Project, CapturedModel


class GeneratorAdapter(Protocol):
    def generate(self, project: Project, mode: Literal['nominal', 'toolpath']) -> CapturedModel:
        ...
