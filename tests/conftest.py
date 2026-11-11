import json
from pathlib import Path

import pytest

CALIBRATION_PATH = (
    Path(__file__).parents[1] / "docs" / "callibration" / "piastq_2026-09-24.json"
)


@pytest.fixture
def calibration_path():
    return CALIBRATION_PATH


@pytest.fixture
def calibration():
    with open(CALIBRATION_PATH) as file:
        return json.load(file)
