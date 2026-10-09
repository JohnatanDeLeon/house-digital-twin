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

TEMPLATE = Path(__file__).with_name('walk_template.html')
DATA_MARKER = '/*__WALK_DATA__*/null'
MAP_SIZES = {'basecolor': 1024, 'normal': 1024, 'roughness': 512, 'opacity': 512}  # px del lado mayor
GLASS_ALPHA = 0.3  # el vidrio de una puerta se deja ver un poco, en vez de desaparecer


def _light_map(src: Path, dst: Path, kind: str, glass: bool = False):
    img = Image.open(src)
    img = img.convert('L' if kind in ('roughness', 'opacity') else 'RGB')
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
                 origin_m=((spec.get('grid') or {}).get('origin_m') or {}), glass=spec.get('glass_material'), maps={})
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


def write_model_script(glb: Path, out: Path):
    """El GLB va dentro de un .js: así lo carga un <script> (los artifacts no sirven .glb y file:// no deja usar fetch)."""
    out.write_text('window.HDT_GLB = "' + base64.b64encode(glb.read_bytes()).decode('ascii') + '";\n')


def build_walk(facts: dict, materials: dict[str, dict], textures_dir: Path, out_dir: Path, glb: Path | None = None):
    """Escribe `index.html`, `texturas/` y, si se da el GLB que exporta Blender, `casa.js`."""
    tex_out = out_dir / 'texturas'
    entries = {name: _material_entry(name, spec, Path(textures_dir) / name, tex_out) for name, spec in materials.items()}
    data = {
        'name': facts['name'],
        'storey_height': facts['levels'][0]['storey_height']['value'],
        'materials': entries,
        'spaces': [{'id': s['id'], 'name': s['name'] or 'Sin rótulo', 'polygon': s['polygon'], 'exterior': s['is_exterior']}
                   for s in facts['spaces']],
        'walls': [w['footprint'] for w in facts['walls']],
        'site': facts['site']['polygon'],
        'sun': [round(c, 4) for c in sun_direction()],
        'entrance': entrance(facts),
    }
    html = TEMPLATE.read_text()
    if DATA_MARKER not in html:
        raise ValueError(f'La plantilla del recorrido no tiene el marcador {DATA_MARKER}')
    out_dir.mkdir(parents=True, exist_ok=True)
    if glb is not None:
        write_model_script(glb, out_dir / 'casa.js')
    (out_dir / 'index.html').write_text(html.replace(DATA_MARKER, json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    return out_dir / 'index.html'
