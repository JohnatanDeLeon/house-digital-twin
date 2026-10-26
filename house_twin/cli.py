"""Línea de comandos: `python -m house_twin.cli build` regenera hechos, IFC y validación."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# El DXF es la fuente primaria; el PDF queda como validación (`compare`)
DEFAULT_SOURCE = ROOT / 'data' / 'raw' / 'plano.dxf'
OWNER_ANNOTATIONS = ROOT / 'sources' / 'owner-annotations.json'
FACTS_PATH = ROOT / 'data' / 'facts' / 'existing.facts.json'
IFC_PATH = ROOT / 'models' / 'existing.ifc'
VARIANTS_IFC_DIR = ROOT / 'models' / 'variants'
OVERLAY_PATH = ROOT / 'docs' / 'analysis' / '02-hechos-planta-existente.png'
VIEWER_PATH = ROOT / 'docs' / 'viewer' / 'casa-jonhy-3d.html'
TEXTURES_DIR = ROOT / 'assets' / 'textures'
BLEND_PATH = ROOT / 'models' / 'existing.blend'
RENDERS_DIR = ROOT / 'docs' / 'analysis' / '05-renders'
WALK_DIR = ROOT / 'docs' / 'viewer' / 'recorrido'
GLB_PATH = ROOT / 'models' / 'existing.glb'
VARIANT_FACTS_DIR = ROOT / 'data' / 'facts' / 'variants'


def variant_facts_path(variant: dict) -> Path:
    return VARIANT_FACTS_DIR / f"{variant['id']}.facts.json"


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
    from house_twin.electrical import load_device_spec
    from house_twin.facts.builder import build_facts
    from house_twin.finishes import Finishes, load_materials
    from house_twin.ifc_export import build_ifc
    from house_twin.furniture import load_furniture
    from house_twin.hardware import load_hardware
    from house_twin.kitchen import load_kitchen
    from house_twin.living import load_living
    from house_twin.bedroom import load_bedrooms
    from house_twin.laundry import load_laundry
    from house_twin.lighting import load_luminaires
    from house_twin.plumbing import load_sanitary_specs, load_shower_spec
    from house_twin.render import render_facts
    from house_twin.variants import (apply_variant, has_geometry, load_variants, validate, variant_facts,
                                     variant_bedrooms, variant_materials, variant_specs)
    from house_twin.viewer import render_viewer
    facts = build_facts(_load_drawing(source), load_annotations(OWNER_ANNOTATIONS))
    FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FACTS_PATH.write_text(json.dumps(facts, ensure_ascii=False, indent=1))
    IFC_PATH.parent.mkdir(parents=True, exist_ok=True)
    materials = load_materials(TEXTURES_DIR)
    finishes = Finishes(facts, materials)
    hardware, furniture, luminaires, devices = load_hardware(), load_furniture(), load_luminaires(), load_device_spec()
    shower, sanitary, kitchen, living = load_shower_spec(), load_sanitary_specs(), load_kitchen(), load_living()
    bedrooms, laundry = load_bedrooms(), load_laundry()
    build_ifc(facts, finishes, hardware, furniture, luminaires, devices, shower, sanitary, kitchen, living, bedrooms,
              laundry).write(str(IFC_PATH))
    render_facts(facts, OVERLAY_PATH)
    render_viewer(facts, VIEWER_PATH)
    print(f"{len(facts['spaces'])} espacios, {len(facts['walls'])} muros, {len(facts['openings'])} vanos")
    outputs = [FACTS_PATH, IFC_PATH, OVERLAY_PATH, VIEWER_PATH]
    for variant in load_variants():  # propuestas: sus hechos y su IFC; la casa existente no cambia
        problems = validate(variant, facts, materials)
        if problems:
            raise SystemExit('\n'.join(problems))
        proposed = variant_facts(facts, variant)
        specs = variant_specs(variant, {'kitchen': kitchen, 'laundry': laundry, 'extras': None, 'living': living})
        if has_geometry(variant):  # remodelación: sus hechos propuestos quedan escritos (los usa `scene`)
            VARIANT_FACTS_DIR.mkdir(parents=True, exist_ok=True)
            variant_facts_path(variant).write_text(json.dumps(proposed, ensure_ascii=False, indent=1))
            outputs.append(variant_facts_path(variant))
        path = VARIANTS_IFC_DIR / f"{variant['id']}.ifc"
        path.parent.mkdir(parents=True, exist_ok=True)
        build_ifc(proposed, apply_variant(Finishes(proposed, variant_materials(materials, variant)), variant, materials), hardware, furniture,
                  luminaires, devices, shower, sanitary, specs['kitchen'], specs['living'], variant_bedrooms(variant, bedrooms),
                  specs['laundry'], specs['extras']).write(str(path))
        outputs.append(path)
    for path in outputs:
        print(f'→ {path.relative_to(ROOT)}')


def compare(source_a: Path, source_b: Path):
    from house_twin.compare import compare_facts
    from house_twin.facts.builder import build_facts
    report = compare_facts(build_facts(_load_drawing(source_a)), build_facts(_load_drawing(source_b)))
    print(json.dumps(report, ensure_ascii=False, indent=1))


def inspect_dxf(source: Path):
    from house_twin.sources.dxf import inventory
    print(json.dumps(inventory(str(source)), ensure_ascii=False, indent=1))


def texture(spec: Path):
    from house_twin.textures import build_texture
    out = build_texture(spec.resolve())
    for f in sorted(out.iterdir()):
        print(f'→ {f.relative_to(ROOT)}')


def hang(spec: Path):
    """Solo la versión colgada de una prenda, a partir de sus mapas extendidos: no necesita la foto."""
    from house_twin.hanging import build_hanging
    for folder in build_hanging(json.loads(spec.read_text())):
        print(f'→ {folder.relative_to(ROOT)}')


def closet_extras(facts: dict) -> tuple[list[dict], list[dict]]:
    """De los closets con interior: las hojas de abajo (se abren) y las prendas que se pueden sacar en el recorrido."""
    from house_twin.closet_interior import display_parts, leaf_parts
    from house_twin.furniture import load_furniture
    specs = {f['applies_to']['space']: f for f in load_furniture()}
    height = facts['levels'][0]['storey_height']['value']
    doors, items = [], []
    for fx in facts.get('fixtures', []):
        spec = specs.get(fx['space'], {})
        if fx['kind'] == 'closet' and 'interior' in spec:
            doors += leaf_parts(fx, spec, height)[1]
            items += display_parts(fx, spec)[1]
    return doors, items


def _blender(ifc: Path, blend: Path, glb: Path, facts: Path, renders: Path | None = None, variant: Path | None = None):
    """Corre `blender_scene.py` dentro de Blender: IFC + texturas → escena con materiales, GLB y (opcional) renders."""
    import shutil
    import subprocess
    blender = shutil.which('blender')
    if blender is None:
        raise SystemExit('No encuentro `blender` en el PATH (ver README: Blender + Bonsai)')
    args = [blender, '--background', '--python', str(ROOT / 'house_twin' / 'blender_scene.py'), '--',
            str(ROOT), str(ifc), str(blend), '--glb', str(glb), '--facts', str(facts)]
    args += ['--render', str(renders)] if renders else []
    args += ['--variant', str(variant)] if variant else []
    out = subprocess.run(args, capture_output=True, text=True)
    report = [line for line in out.stdout.splitlines() if line.startswith(('materiales:', 'sin acabado:', 'Error'))]
    print('\n'.join(report))
    if out.returncode != 0 or not blend.exists():
        raise SystemExit(out.stderr[-2000:] or 'Blender falló')


def scene(render: bool):
    """Escena de Blender con los acabados, recorrido web y (opcional) renders. Cada variante con geometría (una
    remodelación) pasa también por Blender y el recorrido la ofrece con su propio modelo."""
    from house_twin.finishes import load_materials
    from house_twin.variants import VARIANTS_DIR, has_geometry, load_variants
    from house_twin.walk import build_walk
    _blender(IFC_PATH, BLEND_PATH, GLB_PATH, FACTS_PATH, RENDERS_DIR if render else None)
    outputs = [BLEND_PATH, GLB_PATH]
    variants, models = load_variants(), {}
    for variant in [v for v in variants if has_geometry(v)]:
        blend, glb = (VARIANTS_IFC_DIR / f"{variant['id']}{ext}" for ext in ('.blend', '.glb'))
        _blender(VARIANTS_IFC_DIR / f"{variant['id']}.ifc", blend, glb, variant_facts_path(variant),
                 variant=VARIANTS_DIR / f"{variant['id']}.json")
        proposed = json.loads(variant_facts_path(variant).read_text())
        doors, items = closet_extras(proposed)
        models[variant['id']] = {'facts': proposed, 'glb': glb, 'doors': doors, 'items': items}
        outputs += [blend, glb]
    facts = json.loads(FACTS_PATH.read_text())
    doors, items = closet_extras(facts)
    walk = build_walk(facts, load_materials(TEXTURES_DIR), TEXTURES_DIR, WALK_DIR, GLB_PATH, variants, doors, items, models)
    for path in outputs + [walk] + (sorted(RENDERS_DIR.glob('*.jpg')) if render else []):
        print(f'→ {path.relative_to(ROOT)}')


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
    t = sub.add_parser('texture', help='foto → texturas PBR según un JSON de sources/texturas/')
    t.add_argument('spec', type=Path)
    h = sub.add_parser('hang', help='prenda colgada a partir de sus mapas extendidos (no necesita la foto)')
    h.add_argument('spec', type=Path)
    sc = sub.add_parser('scene', help='IFC + texturas → escena de Blender y recorrido web (docs/viewer/recorrido/)')
    sc.add_argument('--render', action='store_true', help='también renderiza las vistas previas (Cycles, CPU: ~5 min)')
    args = parser.parse_args()
    if args.command == 'build':
        build(args.source)
    elif args.command == 'compare':
        compare(args.source_a, args.source_b)
    elif args.command == 'inspect-dxf':
        inspect_dxf(args.source)
    elif args.command == 'texture':
        texture(args.spec)
    elif args.command == 'hang':
        hang(args.spec)
    elif args.command == 'scene':
        scene(args.render)


if __name__ == '__main__':
    main()
