"""Recorrido web en primera persona: la escena de Blender (GLB) + texturas ligeras + una página three.js.

Sale en `docs/viewer/recorrido/` y se abre igual en la PC (teclado y mouse) que en el celular (joystick táctil).
El GLB trae geometría, UV en metros y el nombre del material de cada cara; aquí se preparan las texturas en un
tamaño que un celular carga rápido y los datos de cada material (escala real, alineación de juntas, vidrio).
"""
import base64
import json
from pathlib import Path

from PIL import Image

from house_twin.finishes import _inside
from house_twin.sunlight import sun_direction
from house_twin.variants import opening_overrides

TEMPLATE = Path(__file__).with_name('walk_template.html')
DATA_MARKER = '/*__WALK_DATA__*/null'
MAP_SIZES = {'basecolor': 1024, 'normal': 1024, 'roughness': 512, 'opacity': 512, 'metallic': 512}  # px del lado mayor
GLASS_ALPHA = 0.3  # el vidrio de una puerta se deja ver un poco, en vez de desaparecer


def _light_map(src: Path, dst: Path, kind: str, glass: bool = False):
    img = Image.open(src)
    img = img.convert('L' if kind in ('roughness', 'opacity', 'metallic') else 'RGB')
    img.thumbnail((MAP_SIZES[kind], MAP_SIZES[kind]), Image.LANCZOS)
    if kind == 'opacity' and glass:  # 0 = vidrio, 1 = hoja → alfa del visor; sin vidrio, el hueco queda en 0
        img = img.point(lambda v: round(255 * (GLASS_ALPHA + (1 - GLASS_ALPHA) * v / 255)))
    img.save(dst, quality=90 if kind == 'normal' else 82)


def _material_entry(name: str, spec: dict, folder: Path, out: Path) -> dict:
    entry = {'kind': spec.get('kind', 'maps')}
    if entry['kind'] == 'constant':
        entry['pbr'] = spec['pbr']
        return entry
    entry.update(tileable=bool(spec.get('tileable')), size_m=[spec['size_m']['width'], spec['size_m']['height']],
                 origin_m=((spec.get('grid') or {}).get('origin_m') or {}), glass=spec.get('glass_material'), maps={},
                 emissive=spec.get('emissive'))
    (out / name).mkdir(parents=True, exist_ok=True)
    for kind in MAP_SIZES:
        src = next(iter(sorted(folder.glob(f'{kind}.*'))), None)
        if src is None:
            continue
        _light_map(src, out / name / f'{kind}.jpg', kind, glass=bool(spec.get('glass_material')))
        entry['maps'][kind] = f'texturas/{name}/{kind}.jpg'
    return entry


ENTRANCE_STEP_M = 0.9  # se empieza un paso adentro de la puerta principal


def entrance(facts: dict) -> dict | None:
    """Un paso adentro de la puerta que une el espacio interior más grande con el exterior, mirando hacia adentro."""
    spaces = {s['id']: s for s in facts['spaces']}
    main = max((s for s in facts['spaces'] if not s['is_exterior']), key=lambda s: s['area'])
    door = next((o for o in facts['openings'] if o['kind'] == 'door' and o['footprint'] and main['id'] in o['connects']
                 and any(spaces[c]['is_exterior'] for c in o['connects'])), None)
    if door is None:
        return None
    xs, ys = [p[0] for p in door['footprint']], [p[1] for p in door['footprint']]
    cx, cy = sum(xs) / 4, sum(ys) / 4
    across = (0.0, 1.0) if max(xs) - min(xs) >= max(ys) - min(ys) else (1.0, 0.0)  # perpendicular al muro
    poly = main['polygon']
    if not _inside((cx + across[0] * ENTRANCE_STEP_M, cy + across[1] * ENTRANCE_STEP_M), poly):
        across = (-across[0], -across[1])
    return {'door': door['id'], 'at': [round(cx + across[0] * ENTRANCE_STEP_M, 3), round(cy + across[1] * ENTRANCE_STEP_M, 3)],
            'facing': list(across)}


DOOR_PROBE_M = 0.3  # se prueba a este lado de la hoja para saber hacia qué espacio abre


def doors(facts: dict) -> list[dict]:
    """Puertas que se abren en el recorrido: por hoja, la bisagra, el canto de la chapa y hacia dónde gira.

    Salen del abatimiento de los hechos (bloque PUERTA del plano) o de las hojas que declara el dueño (`leaves`).
    Una corrediza (`slide`) no gira: lleva su hoja cerrada como única «hoja» (para saber qué tan cerca está el
    jugador) y cuánto se desliza (`slide`). Una puerta sin ese dato no se abre: queda cerrada, como un muro."""
    spaces = {s['id']: s for s in facts['spaces']}
    result = []
    for o in facts['openings']:
        if o['kind'] == 'door' and o.get('slide'):
            (ax, ay), (bx, by) = o['slide']['line']
            result.append({'id': o['id'], 'slide': o['slide']['travel'],
                           'leaves': [{'hinge': [ax, ay], 'latch': [bx, by], 'opens_toward': [0.0, 0.0], 'assumed': False}]})
            continue
        leaves = o.get('leaves') or ([o['swing']] if o.get('swing') else [])
        if o['kind'] != 'door' or not o['footprint'] or not leaves:
            continue
        out = []
        for leaf in leaves:
            (hx, hy), (lx, ly) = leaf['hinge_end'], leaf['latch_end']
            length = ((lx - hx) ** 2 + (ly - hy) ** 2) ** 0.5
            n = (-(ly - hy) / length, (lx - hx) / length)
            mid = ((hx + lx) / 2, (hy + ly) / 2)
            into = spaces.get(leaf.get('opens_into'))
            if into and not _inside((mid[0] + n[0] * DOOR_PROBE_M, mid[1] + n[1] * DOOR_PROBE_M), into['polygon']):
                n = (-n[0], -n[1])
            out.append({'hinge': [hx, hy], 'latch': [lx, ly], 'opens_toward': [round(n[0], 4), round(n[1], 4)],
                        'assumed': 'supuesto' in leaf.get('source', '')})
        result.append({'id': o['id'], 'leaves': out})
    return result


STREET_STEP_M = 1.8  # el recorrido empieza en la banqueta, a esta distancia de la puerta de la calle


def street_start(facts: dict) -> dict | None:
    """En la calle, frente a la puerta que lleva al espacio exterior de la entrada principal (la reja del pórtico)."""
    door = entrance(facts)
    if door is None:
        return None
    entry = next(o for o in facts['openings'] if o['id'] == door['door'])
    spaces = {s['id']: s for s in facts['spaces']}
    porch = next((c for c in entry['connects'] if spaces[c]['is_exterior']), None)
    street_y = min(p[1] for p in facts['site']['polygon'])
    gate = next((o for o in facts['openings'] if o['kind'] == 'door' and o['footprint'] and o['connects'] == [porch]
                 and min(p[1] for p in o['footprint']) <= street_y + 0.01), None)
    if gate is None:
        return None
    cx = sum(p[0] for p in gate['footprint']) / 4
    return {'door': gate['id'], 'at': [round(cx, 3), round(street_y - STREET_STEP_M, 3)], 'facing': [0.0, 1.0]}


FOCUS_DISTANCE_M = 2.3  # al elegir una propuesta, se mira lo que cambia de cuerpo entero, también en el celular


def focus(facts: dict, opening_id: str) -> dict | None:
    """Punto frente a un vano, del lado del espacio interior más grande, mirándolo (para mostrar una propuesta)."""
    door = next((o for o in facts['openings'] if o['id'] == opening_id and o['footprint']), None)
    if door is None:
        return None
    spaces = {s['id']: s for s in facts['spaces']}
    p0, p1, _, p3 = door['footprint']
    a, b = (p1[0] - p0[0], p1[1] - p0[1]), (p3[0] - p0[0], p3[1] - p0[1])
    across = b if (a[0] ** 2 + a[1] ** 2) >= (b[0] ** 2 + b[1] ** 2) else a  # perpendicular al vano
    norm = (across[0] ** 2 + across[1] ** 2) ** 0.5
    across = (across[0] / norm, across[1] / norm)
    cx, cy = sum(p[0] for p in door['footprint']) / 4, sum(p[1] for p in door['footprint']) / 4
    sides = sorted((spaces[c] for c in door['connects'] if c in spaces), key=lambda s: (s['is_exterior'], -s['area']))
    for sign in (1, -1):
        at = (cx + sign * across[0] * FOCUS_DISTANCE_M, cy + sign * across[1] * FOCUS_DISTANCE_M)
        if sides and _inside(at, sides[0]['polygon']):
            return {'at': [round(at[0], 3), round(at[1], 3)], 'facing': [-sign * across[0], -sign * across[1]]}
    return None


def write_model_script(glb: Path, out: Path):
    """El GLB va dentro de un .js: así lo carga un <script> (los artifacts no sirven .glb y file:// no deja usar fetch)."""
    out.write_text('window.HDT_GLB = "' + base64.b64encode(glb.read_bytes()).decode('ascii') + '";\n')


def house_data(facts: dict, extra_doors: list[dict] | None = None, items: list[dict] | None = None) -> dict:
    """Lo del recorrido que sale de los hechos: espacios, muros, puertas, prendas y por dónde se empieza."""
    return {
        'name': facts['name'],
        'storey_height': facts['levels'][0]['storey_height']['value'],
        'spaces': [{'id': s['id'], 'name': s['name'] or 'Sin rótulo', 'polygon': s['polygon'], 'exterior': s['is_exterior']}
                   for s in facts['spaces']],
        'walls': [w['footprint'] for w in facts['walls']],
        'site': facts['site']['polygon'],
        'entrance': entrance(facts),
        'start': street_start(facts),
        'doors': doors(facts) + (extra_doors or []),  # además de las puertas, las hojas de los closets
        'items': items or [],  # cosas que se pueden sacar y ver de cerca (una prenda del closet)
    }


def _variant_entry(variant: dict, facts: dict, model: dict | None) -> dict:
    """Una propuesta en el selector. Con geometría (`model`) trae su modelo (`casa-<id>.js`) y sus propios datos de
    la casa; si no, los materiales que cambia sobre el modelo de la casa."""
    house = facts if model is None else model['facts']
    target = variant.get('focus_opening') or next((c['opening'] for c in variant.get('changes', [])), None)
    entry = {'id': variant['id'], 'name': variant['name'], 'description': variant['description'],
             'disclaimer': variant.get('disclaimer'), 'overrides': opening_overrides(variant),
             'focus': variant.get('focus') or (focus(house, target) if target else None)}  # `focus`: punto de vista declarado
    if model is not None:
        entry.update(model=f"casa-{variant['id']}.js", house=house_data(house, model['doors'], model['items']))
    return entry


def build_walk(facts: dict, materials: dict[str, dict], textures_dir: Path, out_dir: Path, glb: Path | None = None,
               variants: list[dict] | None = None, extra_doors: list[dict] | None = None,
               items: list[dict] | None = None, models: dict[str, dict] | None = None):
    """Escribe `index.html`, `texturas/` y, si se da el GLB que exporta Blender, `casa.js`.

    Con `variants`, el recorrido ofrece cada propuesta junto a la casa actual. Una propuesta de acabados cambia los
    materiales que toca; una remodelación (con su entrada en `models`: hechos propuestos, GLB, hojas de closet y
    prendas) se recorre con su propio modelo, `casa-<id>.js`.
    """
    models = models or {}
    tex_out = out_dir / 'texturas'
    entries = {name: _material_entry(name, spec, Path(textures_dir) / name, tex_out) for name, spec in materials.items()}
    data = {**house_data(facts, extra_doors, items), 'materials': entries, 'sun': [round(c, 4) for c in sun_direction()],
            'variants': [_variant_entry(v, facts, models.get(v['id'])) for v in variants or []]}
    html = TEMPLATE.read_text()
    if DATA_MARKER not in html:
        raise ValueError(f'La plantilla del recorrido no tiene el marcador {DATA_MARKER}')
    out_dir.mkdir(parents=True, exist_ok=True)
    if glb is not None:
        write_model_script(glb, out_dir / 'casa.js')
    for variant_id, model in models.items():
        write_model_script(model['glb'], out_dir / f'casa-{variant_id}.js')
    (out_dir / 'index.html').write_text(html.replace(DATA_MARKER, json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    return out_dir / 'index.html'
