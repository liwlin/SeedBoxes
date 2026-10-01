"""Instrument one generator instance, never upstream global classes."""
from copy import deepcopy
from affine import Affine
from boxes.generators.closedbox import ClosedBox


class CapturingClosedBox(ClosedBox):
    UI = 'web'

    def __init__(self):
        super().__init__()
        self.captured_walls = []
        self._capture_frame = None
        self._active_wall = None

    def rectangularWall(self, x, y, edges='eeee', *args, **kwargs):
        # ClosedBox has six high-level walls; helpers that only move must not create panels.
        if 'only' in (kwargs.get('move') or '').split():
            return super().rectangularWall(x, y, edges, *args, **kwargs)
        before = {id(p): len(p.pathes) for p in self.surface.parts}
        self._capture_frame = None
        self._active_wall = kwargs.get('label', '')
        try:
            super().rectangularWall(x, y, edges, *args, **kwargs)
            if self._capture_frame is None:
                raise ValueError('未捕获板件内腔参考坐标')
            paths = [deepcopy(path) for part in self.surface.parts
                     for path in part.pathes[before.get(id(part), 0):]
                     if path.path and not any(c[0] == 'T' for c in path.path)]
            self.captured_walls.append({
                'role': self._active_wall, 'width': x, 'height': y,
                'edges': tuple(e if isinstance(e,str) else e.char for e in edges),
                'canvasToLocal': ~self._capture_frame, 'paths': paths,
            })
        finally:
            self._active_wall = None
            self._capture_frame = None

    def cc(self, callback, number, x=0., y=None, a=0.):
        if self._active_wall is not None and number == 0 and self._capture_frame is None:
            # This is the actual callback frame, including edge startwidth and burn correction.
            self._capture_frame = self.ctx._m * Affine.translation(x, self.burn if y is None else y)
        return super().cc(callback, number, x, y, a)
