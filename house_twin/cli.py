"""Línea de comandos: `python -m house_twin.cli build` regenera hechos, IFC y validación."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / 'sources' / 'casa-jonhy-levantamiento.pdf'
OWNER_ANNOTATIONS = ROOT / 'sources' / 'owner-annotations.json'
FACTS_PATH = ROOT / 'data' / 'facts' / 'existing.facts.json'
IFC_PATH = ROOT / 'models' / 'existing.ifc'
OVERLAY_PATH = ROOT / 'docs' / 'analysis' / '02-hechos-planta-existente.png'
VIEWER_PATH = ROOT / 'docs' / 'viewer' / 'casa-jonhy-3d.html'


def _load_drawing(source: Path):
    source = source.resolve()
    if source.suffix.lower() == '.dxf':
        from house_twin.sources.dxf import load_dxf_drawing
        drawing = load_dxf_drawing(str(source))
    else:
        from house_twin.sources.pdf import load_pdf_drawing
        drawing = load_pdf_drawing(str(source))
    # la procedencia no debe depender de dónde está clonado el repo
    label = source.relative_to(ROOT) if source.is_relative_to(ROOT) else source.name
    drawing.source = f"{source.suffix.lower().lstrip('.')}:{label}"
    return drawing


def build(source: Path):
    from house_twin.facts.annotations import load_annotations
    from house_twin.facts.builder import build_facts
    from house_twin.ifc_export import build_ifc
    from house_twin.render import render_facts
    from house_twin.viewer import render_viewer
    facts = build_facts(_load_drawing(source), load_annotations(OWNER_ANNOTATIONS))
    FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FACTS_PATH.write_text(json.dumps(facts, ensure_ascii=False, indent=1))
    IFC_PATH.parent.mkdir(parents=True, exist_ok=True)
    build_ifc(facts).write(str(IFC_PATH))
    render_facts(facts, OVERLAY_PATH)
    render_viewer(facts, VIEWER_PATH)
    print(f"{len(facts['spaces'])} espacios, {len(facts['walls'])} muros, {len(facts['openings'])} vanos")
    for path in (FACTS_PATH, IFC_PATH, OVERLAY_PATH, VIEWER_PATH):
        print(f'→ {path.relative_to(ROOT)}')


def compare(source_a: Path, source_b: Path):
    from house_twin.compare import compare_facts
    from house_twin.facts.builder import build_facts
    report = compare_facts(build_facts(_load_drawing(source_a)), build_facts(_load_drawing(source_b)))
    print(json.dumps(report, ensure_ascii=False, indent=1))


def inspect_dxf(source: Path):
    from house_twin.sources.dxf import inventory
    print(json.dumps(inventory(str(source)), ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(prog='house_twin')
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build', help='plano → hechos → IFC → imagen de validación')
    b.add_argument('--source', type=Path, default=DEFAULT_SOURCE, help='PDF vectorial o DXF')
    c = sub.add_parser('compare', help='compara los hechos de dos fuentes (PDF vs DXF)')
    c.add_argument('source_a', type=Path)
    c.add_argument('source_b', type=Path)
    i = sub.add_parser('inspect-dxf', help='capas, entidades, bloques y unidades de un DXF')
    i.add_argument('source', type=Path)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.source)
    elif args.command == 'compare':
        compare(args.source_a, args.source_b)
    elif args.command == 'inspect-dxf':
        inspect_dxf(args.source)


if __name__ == '__main__':
    main()
