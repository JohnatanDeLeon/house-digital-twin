"""Ida y vuelta: el dibujo del PDF se escribe como DXF (otras unidades, otro origen, puertas como bloque)
y los hechos que salen del DXF deben coincidir con los del PDF."""
import ezdxf
import pytest

from house_twin.compare import compare_facts
from house_twin.facts.annotations import load_annotations
from house_twin.facts.builder import build_facts
from house_twin.sources.dxf import inventory, load_dxf_drawing
from tests.conftest import OWNER

CM_PER_M = 100
OFFSET_CM = (5_000.0, 12_000.0)


def _write_dxf(drawing, path, declare_units=True):
    doc = ezdxf.new('R2018')
    doc.header['$INSUNITS'] = 5 if declare_units else 0  # cm, o sin declarar (ezdxf declara metros por omisión)
    to_cm = lambda p: (p[0] * CM_PER_M + OFFSET_CM[0], p[1] * CM_PER_M + OFFSET_CM[1])
    for layer in drawing.segments:
        if (layer or 'SIN_CAPA') not in doc.layers:
            doc.layers.add(layer or 'SIN_CAPA')
    msp = doc.modelspace()
    door_block = doc.blocks.new('PUERTA_TEST')  # entidades en capa "0" heredan la capa del INSERT
    for a, b in drawing.segments.get('PUERTAS', []):
        door_block.add_line(to_cm(a), to_cm(b), dxfattribs={'layer': '0'})
    msp.add_blockref('PUERTA_TEST', (0, 0), dxfattribs={'layer': 'PUERTAS'})
    for layer, segments in drawing.segments.items():
        if layer == 'PUERTAS':
            continue
        for a, b in segments:
            msp.add_line(to_cm(a), to_cm(b), dxfattribs={'layer': layer or 'SIN_CAPA'})
    for t in drawing.texts:
        msp.add_text(t.value, dxfattribs={'layer': t.layer or 'SIN_CAPA', 'insert': to_cm(t.position)})
    doc.saveas(path)


@pytest.fixture(scope='module', params=[True, False], ids=['units-declared', 'units-inferred'])
def dxf_path(request, pdf_drawing, tmp_path_factory):
    path = tmp_path_factory.mktemp('dxf') / 'casa.dxf'
    _write_dxf(pdf_drawing, str(path), declare_units=request.param)
    return path


def test_dxf_round_trip_reproduces_pdf_facts(dxf_path, facts):
    dxf_facts = build_facts(load_dxf_drawing(str(dxf_path)), load_annotations(OWNER))
    report = compare_facts(facts, dxf_facts)
    assert report['counts']['spaces'] == report['counts']['spaces'][:1] * 2
    assert report['counts']['openings'] == report['counts']['openings'][:1] * 2
    assert report['max_space_area_diff_m2'] <= 0.01
    assert report['max_opening_width_diff_m'] <= 0.002
    assert report['openings_only_in_b'] == []


def test_units_are_inferred_when_not_declared(dxf_path):
    drawing = load_dxf_drawing(str(dxf_path))
    assert drawing.metadata['meters_per_unit'] == pytest.approx(0.01)
    assert drawing.metadata['units_inferred'] == (drawing.metadata['units_declared'] == 0)


def test_inventory_reports_layers_and_blocks(dxf_path):
    inv = inventory(str(dxf_path))
    assert inv['blocks_used'] == {'PUERTA_TEST': 1}
    assert inv['layers']['MUROS']['entities']['LINE'] > 0
