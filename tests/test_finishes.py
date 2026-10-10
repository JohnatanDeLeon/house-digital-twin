from pathlib import Path

import pytest

from house_twin.finishes import Finishes, load_materials
from house_twin.ifc_export import build_ifc

TEXTURES = Path(__file__).resolve().parent.parent / 'assets' / 'textures'


def _material(spaces=None, surface=None, **extra):
    applies = {k: v for k, v in {'spaces': spaces, 'surface': surface}.items() if v is not None}
    return {'applies_to': {**applies, **extra}}


@pytest.fixture
def toy():
    """Dos cuartos interiores (A, baño B) y un patio C, separados por muros de 0.2 m; la calle en Y < 0."""
    facts = {'site': {'polygon': [[0, 0], [0, 5], [6, 5], [6, 0]]},
             'spaces': [{'id': 'A', 'is_exterior': False, 'polygon': [[0.2, 0.2], [2.8, 0.2], [2.8, 2.8], [0.2, 2.8]]},
                        {'id': 'B', 'is_exterior': False, 'polygon': [[3.0, 0.2], [5.8, 0.2], [5.8, 2.8], [3.0, 2.8]]},
                        {'id': 'C', 'is_exterior': True, 'polygon': [[0.2, 3.0], [5.8, 3.0], [5.8, 4.8], [0.2, 4.8]]}]}
    materials = {'yeso': _material(['A', 'B'], 'muros interiores'), 'azulejo': _material(['B'], 'muros'),
                 'aplanado': _material(['C'], 'muros exteriores'), 'estuco': _material([], 'muros exteriores', street_facade=True),
                 'loseta': _material(['A', 'B'], 'piso'), 'antiderrapante': _material(['B'], 'piso de la regadera')}
    return Finishes(facts, materials)


def test_wall_face_takes_the_finish_of_the_space_it_faces(toy):
    assert toy.wall_face((2.8, 1.0), (-1, 0)) == ('yeso', 'A')
    assert toy.wall_face((1.0, 3.0), (0, 1)) == ('aplanado', 'C')


def test_most_specific_finish_wins(toy):
    assert toy.wall_face((3.0, 1.0), (1, 0)) == ('azulejo', 'B')  # el baño está en el yeso y en el azulejo


def test_street_and_neighbour_faces(toy):
    assert toy.wall_face((1.0, 0.0), (0, -1)) == ('estuco', 'calle')
    assert toy.wall_face((0.0, 1.0), (-1, 0)) == (None, 'colindancia')


def test_jamb_prefers_the_interior_side(toy):
    # mocheta de un vano en el muro entre A y C: mira a lo largo del muro, a ningún espacio
    assert toy.wall_face((1.0, 2.9), (1, 0)) == ('yeso', 'A')


def test_floor_ignores_partial_zones(toy):
    assert toy.floor('B') == 'loseta'  # el piso de la regadera es una zona sin geometría propia
    assert toy.floor('C') is None


def test_real_finishes(dxf_facts):
    finishes = Finishes(dxf_facts, load_materials(TEXTURES))
    names = {s['name']: s['id'] for s in dxf_facts['spaces']}
    assert finishes.floor(names['Pórtico']) == 'piso-exterior'
    assert finishes.floor(names['Tragaluz']) == 'piso-interior'
    assert finishes.walls[names['Baño']] == 'azulejo-bano'
    assert finishes.walls[names['Pórtico']] == finishes.street == 'estuco-fachada'
    assert finishes.opening('D03') == {'leaf': 'puerta-entrada', 'glass': 'vidrio-polarizado'}
    assert finishes.opening('V01') == {'frame': 'aluminio-negro', 'glass': 'vidrio-claro'}


def test_ifc_carries_floor_finishes_and_materials(dxf_facts):
    import ifcopenshell.util.element as ue
    import ifcopenshell.validate
    model = build_ifc(dxf_facts, Finishes(dxf_facts, load_materials(TEXTURES)))
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    floors = {c.Name: ue.get_material(c).Name for c in model.by_type('IfcCovering') if c.PredefinedType == 'FLOORING'}
    assert len(floors) == len(dxf_facts['spaces']) + 1  # el baño lleva además el piso de la regadera
    assert floors.pop('S05-regadera') == 'piso-regadera'
    assert set(floors.values()) == {'piso-interior', 'piso-exterior'}
    bano = next(c for c in model.by_type('IfcCovering') if c.Name == 'S05-piso')
    assert ue.get_psets(bano)['HDT_Provenance']['Finish'] == 'piso-interior'
    ceilings = {c.Name: ue.get_material(c).Name for c in model.by_type('IfcCovering') if c.PredefinedType == 'CEILING'}
    roofed = [s for s in dxf_facts['spaces'] if s['roofed']['value'] is True]
    assert len(ceilings) == len(roofed) and set(ceilings.values()) == {'tirol-techo'}
    d03 = next(d for d in model.by_type('IfcDoor') if d.Name == 'D03')
    parts = {c.Name: c.Material.Name for c in ue.get_material(d03).MaterialConstituents}
    assert parts == {'Hoja': 'puerta-entrada', 'Vidrio': 'vidrio-polarizado'}


def test_opening_remembers_the_side_its_photo_was_taken_from(toy):
    facts = {'site': {'polygon': [[0, 0], [0, 5], [6, 5], [6, 0]]}, 'spaces': []}
    materials = {'puerta': _material(openings=['D01'], viewed_from='C'), 'otra': _material(openings=['D02'])}
    finishes = Finishes(facts, materials)
    assert finishes.viewed_from('D01') == 'C'
    assert finishes.viewed_from('D02') is None


def test_half_bath_tiles_stop_at_2_10(dxf_facts):
    finishes = Finishes(dxf_facts, load_materials(TEXTURES))
    face = ((9.0, 2.03), (0.0, 1.0))  # muro sur del medio baño, mirando hacia adentro
    assert finishes.wall_face(*face, 1.0)[0] == 'azulejo-bano'
    assert finishes.wall_face(*face, 2.3)[0] == 'muro-interior'
    assert finishes.wall_face((3.6, 10.23), (0.0, 1.0), 2.5)[0] == 'azulejo-bano'  # el baño principal, hasta el techo
    assert 2.10 in finishes.wall_split_heights()


def test_kitchen_niche_has_tiles_cenefa_and_paint_above(dxf_facts):
    finishes = Finishes(dxf_facts, load_materials(TEXTURES))
    back = ((2.8, 10.05), (0.0, -1.0))  # muro del fondo del nicho, mirando a la cocina
    assert finishes.wall_face(*back, 1.0)[0] == 'azulejo-cocina'
    assert finishes.wall_face(*back, 1.26)[0] == 'cenefa-cocina'
    assert finishes.wall_face(*back, 2.4)[0] == 'muro-interior'
    assert finishes.wall_face((3.0, 6.88), (0.0, 1.0), 1.0)[0] == 'muro-interior'  # fuera del nicho: sin azulejo
