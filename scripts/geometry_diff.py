"""Compare actual local capture against the independent pinned upstream renderer."""
import json
import math
from pathlib import Path
import sys
from affine import Affine
from boxes.generators.closedbox import ClosedBox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from seedboxes.domain.serialization import normalize_project
from seedboxes.engine.closed_box import ClosedBoxAdapter


def main():
    data=json.loads((ROOT/'tests/fixtures/project.json').read_text(encoding='utf-8'))
    result=ClosedBoxAdapter().generate(normalize_project(data),'nominal')
    box=ClosedBox();box.parseArgs(['--x','120','--y','80','--h','60','--outside','0',
        '--thickness','3','--burn','0','--reference','0','--labels','0','--inner_corners','corner'])
    box.open();box.render()
    by_role={p.sourceRole:p for p in result.panels}
    max_error=0.;points_checked=0
    try:
        for role,part in zip(('Wall 1','Wall 2','Wall 4','Wall 3','Top','Bottom'),[p for p in box.surface.parts if p.pathes]):
            panel=by_role[role];transform=Affine(*panel.canvasToLocal)
            expected=[transform*tuple(c[1:3]) for path in part.pathes for c in path.path if c[0] in ('M','L')]
            actual=[c[1:3] for c in panel.geometry.outer.commands if c[0] in ('M','L')]
            if len(actual)!=len(expected): raise RuntimeError('Path command counts differ')
            for a,b in zip(actual,expected):
                max_error=max(max_error,math.dist(a,b));points_checked+=1
        if max_error>1e-8: raise RuntimeError(f'Geometry drift: {max_error} mm')
        print(json.dumps({'panels':len(result.panels),'pointsCompared':points_checked,'maxErrorMm':max_error}))
    finally:
        box.close()


if __name__=='__main__': main()
