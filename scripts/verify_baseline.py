"""Report the installed upstream engine, without starting a desktop window."""
from importlib.metadata import distribution
import json
import platform
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET


def collect_manifest() -> dict:
    from boxes.formats import Formats
    from boxes.generators import getAllBoxGenerators
    dist = distribution('boxes')
    source = json.loads(dist.read_text('direct_url.json') or '{}')
    commit = source.get('vcs_info', {}).get('commit_id')
    if not commit:
        raise RuntimeError('Installed Boxes.py does not have a verifiable Git commit')
    generators = getAllBoxGenerators()
    return {
        'engineCommit': commit,
        'engineVersion': dist.version,
        'pythonVersion': platform.python_version(),
        'discoveredGenerators': sum(bool(getattr(cls, 'webinterface', True)) for cls in generators.values()),
        'supportedFormats': sorted(Formats().getFormats()),
    }


def svg_summary(generator: str) -> dict:
    from boxes.generators import getAllBoxGenerators
    cls = next(c for c in getAllBoxGenerators().values() if c.__name__ == generator)
    box = cls()
    box.parseArgs(['--x', '120', '--y', '80', '--h', '60', '--thickness', '3',
                   '--burn', '0', '--format', 'svg', '--reference', '0',
                   '--labels', '0', '--qr_code', '0'])
    box.open()
    box.render()
    root = ET.fromstring(box.close().getvalue())
    ns = '{http://www.w3.org/2000/svg}'
    return {'generator': generator, 'width': root.get('width'), 'height': root.get('height'),
            'viewBox': root.get('viewBox'), 'groups': len(root.findall(ns + 'g')),
            'paths': [p.get('d') for p in root.iter(ns + 'path')]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-fixtures', type=Path)
    args = parser.parse_args()
    print(json.dumps(collect_manifest(), indent=2))
    if args.write_fixtures:
        args.write_fixtures.mkdir(parents=True, exist_ok=True)
        for name in ('ClosedBox', 'ABox'):
            (args.write_fixtures / (name + '.json')).write_text(
                json.dumps(svg_summary(name), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
