"""Convert pinned Boxes drawing commands; keep real curves and local offsets."""
from copy import deepcopy
import math
from affine import Affine
from seedboxes.domain.models import Path2D


CLOSURE_EPS = 1e-7


def capture_path(source, canvas_to_local: Affine, path_id: str, operation: str,
                 inner_corners: str) -> Path2D:
    path = deepcopy(source)
    # Upstream SVG applies this at export. Work on a copy so the renderer remains untouched.
    path.faster_edges(inner_corners)
    commands = []
    for command in path.path:
        code = command[0]
        if code not in ('M', 'L', 'C'):
            raise ValueError(f'未支持的制造路径命令：{code}')
        endpoint = canvas_to_local * tuple(command[1:3])
        if code == 'C':
            # Upstream C stores endpoint FIRST; JSON/SVG C stores it LAST.
            first = canvas_to_local * tuple(command[3:5])
            second = canvas_to_local * tuple(command[5:7])
            commands.append(('C', *first, *second, *endpoint))
        else:
            commands.append((code, *endpoint))
    if not commands or commands[0][0] != 'M':
        raise ValueError('切割路径没有起点')
    if sum(c[0] == 'M' for c in commands) != 1:
        raise ValueError('单路径存在多个不连续子轮廓')
    start = commands[0][1:3]
    end = commands[-1][-2:]
    closed = math.dist(start, end) <= CLOSURE_EPS
    if not closed:
        raise ValueError(f'切割轮廓未闭合：{path_id}')
    commands.append(('Z',))
    return Path2D(path_id, tuple(commands), closed, operation)


def path_bounds(path: Path2D) -> tuple[float, float, float, float]:
    """Analytic bounds, including internal extrema of cubic Beziers."""
    points = []
    current = (0., 0.)
    for c in path.commands:
        if c[0] in ('M', 'L'):
            current = (c[1], c[2]); points.append(current)
        elif c[0] == 'C':
            p0=current; p1=c[1:3];p2=c[3:5];p3=c[5:7]
            ts={0.,1.}
            for axis in (0,1):
                a=-p0[axis]+3*p1[axis]-3*p2[axis]+p3[axis]
                b=2*(p0[axis]-2*p1[axis]+p2[axis])
                d=p1[axis]-p0[axis]
                if abs(a)<1e-12:
                    if abs(b)>1e-12: ts.add(-d/b)
                else:
                    disc=b*b-4*a*d
                    if disc>=0:
                        ts.update(((-b+math.sqrt(disc))/(2*a),(-b-math.sqrt(disc))/(2*a)))
            for t in ts:
                if 0<=t<=1:
                    points.append(tuple((1-t)**3*p0[k]+3*(1-t)**2*t*p1[k]+3*(1-t)*t*t*p2[k]+t**3*p3[k] for k in (0,1)))
            current=tuple(p3)
    if not points:
        raise ValueError('空路径')
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)
