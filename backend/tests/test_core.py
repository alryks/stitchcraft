import numpy as np

from app.color import delta_e, rgb_to_lab
from app.regions import components


def test_rgb_lab_and_delta_e_identity():
    lab = rgb_to_lab(np.array([[[255, 0, 0]]], dtype=np.uint8))
    assert lab.shape == (1, 1, 3)
    assert float(delta_e(lab, lab)[0, 0]) == 0.0


def test_connected_components():
    values = np.array([[1, 1, 2], [1, 2, 2], [3, 3, 2]])
    assert sorted(map(len, components(values))) == [2, 3, 4]

