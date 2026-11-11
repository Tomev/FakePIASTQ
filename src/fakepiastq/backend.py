"""Aer simulator configured as the PIAST-Q device."""

import json
from pathlib import Path
from typing import Self

from qiskit_aer import AerSimulator

from fakepiastq.noise import fake_piastq_noise_model


class FakePiast(AerSimulator):
    """`AerSimulator` with the PIAST-Q noise model, native gates and qubit count.

    Create it with `from_file` or `from_dict`. In both, remaining keyword
    arguments are passed to `AerSimulator`.
    """

    @classmethod
    def from_file(cls, calibration_path: str | Path, **options) -> Self:
        """Create the backend from a calibration JSON file."""
        with open(calibration_path) as file:
            return cls.from_dict(json.load(file), **options)

    @classmethod
    def from_dict(cls, calibration: dict, **options) -> Self:
        """Create the backend from the content of a calibration JSON file."""
        return cls(
            noise_model=fake_piastq_noise_model(calibration),
            n_qubits=calibration["n_qubits"],
            **options,
        )
