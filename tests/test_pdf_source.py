import pytest


def test_pdf_keeps_cad_layers(pdf_drawing):
    assert len(pdf_drawing.metadata['layers']) == 22
    assert {'MUROS', 'VANOS', 'VENTANAS', 'PUERTAS'} <= set(pdf_drawing.metadata['layers'])


def test_scale_is_calibrated_not_taken_from_title_block(pdf_drawing):
    cal = pdf_drawing.metadata['calibration']
    assert cal['pt_per_m'] == pytest.approx(36.6355, abs=1e-3)
    assert cal['paper_scale'] == pytest.approx(77.4, abs=0.1)  # el cajetín dice 1:100


def test_partial_dimensions_close_within_one_centimetre(pdf_drawing):
    residuals = pdf_drawing.metadata['calibration']['dimension_residuals_m']
    partial = [r for value, r in residuals if value < 10]
    assert max(abs(r) for r in partial) <= 0.01


def test_room_labels_are_decoded(pdf_drawing):
    values = {t.value for t in pdf_drawing.texts_for('room_labels')}
    assert {'RECAMARA 1', 'BAÑO', 'COCINA', 'BODEGA'} <= values
