from pathlib import Path

import pytest

from house_twin.facts.annotations import load_annotations
from house_twin.facts.builder import build_facts
from house_twin.sources.dxf import load_dxf_drawing
from house_twin.sources.pdf import load_pdf_drawing

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / 'sources' / 'casa-jonhy-levantamiento.pdf'
OWNER = ROOT / 'sources' / 'owner-annotations.json'
DXF = ROOT / 'data' / 'raw' / 'plano.dxf'


@pytest.fixture(scope='session')
def pdf_drawing():
    return load_pdf_drawing(str(PDF))


@pytest.fixture(scope='session')
def plan_only_facts(pdf_drawing):
    return build_facts(pdf_drawing)


@pytest.fixture(scope='session')
def facts(pdf_drawing):
    return build_facts(pdf_drawing, load_annotations(OWNER))


@pytest.fixture(scope='session')
def dxf_facts():
    """Hechos del plano real (la fuente primaria del modelo), no del PDF de validación."""
    return build_facts(load_dxf_drawing(str(DXF)), load_annotations(OWNER))


def space_named(facts, name):
    return next(s for s in facts['spaces'] if s['name'] == name)
