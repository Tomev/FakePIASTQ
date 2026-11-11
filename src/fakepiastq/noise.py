"""Qiskit Aer noise model for PIAST-Q, built from a calibration snapshot."""

import json
from pathlib import Path

from qiskit.quantum_info import average_gate_fidelity
from qiskit_aer.noise import (
    NoiseModel,
    QuantumError,
    ReadoutError,
    depolarizing_error,
    thermal_relaxation_error,
)

# AQT native gates. RZ is virtual (a frame update), so it carries no error.
BASIS_GATES = ["r", "rz", "rxx"]

# Resolves inside a source checkout (uv installs the project as editable).
DEFAULT_CALIBRATION = (
    Path(__file__).parents[2] / "docs" / "callibration" / "piastq_2026-09-24.json"
)


def fake_piastq_noise_model(
    calibration_path: str | Path = DEFAULT_CALIBRATION,
) -> NoiseModel:
    """Build the PIAST-Q noise model from a calibration JSON file.

    Each R and RXX gate gets thermal relaxation over its duration, followed by
    depolarizing noise sized so the total matches the reported gate fidelity
    (taken as the average gate fidelity of the native gate). Measurements get
    a symmetric readout error from the SPAM fidelity. Idle noise and crosstalk
    are not modelled.
    """
    with open(calibration_path) as file:
        data = json.load(file)["vendor"]["characterisation"]

    t1 = data["t1_s"]["value"]
    t2 = data["t2_coherence_time_s"]["value"]
    relaxation_1q = thermal_relaxation_error(
        t1, t2, data["single_qubit_gate_duration_micros"] * 1e-6
    )
    relaxation_2q_single = thermal_relaxation_error(
        t1, t2, data["two_qubit_gate_duration_micros"] * 1e-6
    )
    relaxation_2q = relaxation_2q_single.expand(relaxation_2q_single)

    noise_model = NoiseModel(basis_gates=BASIS_GATES)

    for qubit, fidelity in data["single_qubit_gate_fidelity"].items():
        error = _gate_error(relaxation_1q, 1 - fidelity["value"] / 100)
        noise_model.add_quantum_error(error, "r", [int(qubit)])

    # Only a chain-average 2Q fidelity is published, so every pair shares it.
    error_2q = 1 - data["mean_two_qubit_gate_fidelity"]["value"] / 100
    noise_model.add_all_qubit_quantum_error(
        _gate_error(relaxation_2q, error_2q), "rxx"
    )

    # One SPAM figure covers preparation and measurement; all of it is put on
    # measurement, with equal 0->1 and 1->0 flip probabilities.
    flip = 1 - data["spam_fidelity_lower_bound"] / 100
    noise_model.add_all_qubit_readout_error(
        ReadoutError([[1 - flip, flip], [flip, 1 - flip]])
    )

    return noise_model


def _gate_error(relaxation: QuantumError, target_infidelity: float) -> QuantumError:
    """Top `relaxation` up with depolarizing noise to reach `target_infidelity`.

    If relaxation alone already exceeds the target, it is returned unchanged
    and the gate ends up noisier than reported.
    """
    num_qubits = relaxation.num_qubits
    dim = 2**num_qubits
    relaxation_fidelity = average_gate_fidelity(relaxation)
    if target_infidelity <= 1 - relaxation_fidelity:
        return relaxation

    # A depolarizing channel with parameter p after a channel with fidelity F
    # gives (1 - p) * F + p / dim. Solve for the p that hits the target.
    depolarizing_param = (relaxation_fidelity - (1 - target_infidelity)) / (
        relaxation_fidelity - 1 / dim
    )
    return relaxation.compose(depolarizing_error(depolarizing_param, num_qubits))
