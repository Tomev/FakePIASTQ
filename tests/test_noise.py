import math

import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import average_gate_fidelity
from qiskit_aer import AerSimulator

from fakepiastq import fake_piastq_noise_model

# Qubits whose reported 1Q error is below what relaxation alone produces.
CLIPPED_QUBITS = {9, 10}


@pytest.fixture
def characterisation(calibration):
    return calibration["vendor"]["characterisation"]


@pytest.fixture
def noise_model(calibration):
    return fake_piastq_noise_model(calibration)


def _local_error(noise_model, gate, qubits):
    return noise_model._local_quantum_errors[gate][tuple(qubits)]


def test_single_qubit_errors_match_reported_fidelities(noise_model, characterisation):
    for qubit, reported in characterisation["single_qubit_gate_fidelity"].items():
        qubit = int(qubit)
        fidelity = average_gate_fidelity(_local_error(noise_model, "r", [qubit]))
        if qubit in CLIPPED_QUBITS:
            assert fidelity < reported["value"] / 100
        else:
            assert math.isclose(fidelity, reported["value"] / 100, abs_tol=1e-9)


def test_two_qubit_error_matches_reported_fidelity(noise_model, characterisation):
    fidelity = average_gate_fidelity(noise_model._default_quantum_errors["rxx"])
    reported = characterisation["mean_two_qubit_gate_fidelity"]["value"] / 100
    assert math.isclose(fidelity, reported, abs_tol=1e-9)


def test_readout_error_matches_spam_fidelity(noise_model, characterisation):
    probabilities = noise_model._default_readout_error.probabilities
    spam = characterisation["spam_fidelity_lower_bound"] / 100
    assert probabilities[0] == pytest.approx([spam, 1 - spam])
    assert probabilities[1] == pytest.approx([1 - spam, spam])


def test_rz_is_noiseless(noise_model):
    assert "rz" not in noise_model.noise_instructions


def test_simulation_shows_noise(noise_model):
    circuit = QuantumCircuit(2)
    circuit.r(math.pi / 2, 0, 0)
    for _ in range(20):
        circuit.rxx(math.pi / 2, 0, 1)
    circuit.measure_all()

    simulator = AerSimulator(noise_model=noise_model)
    counts = simulator.run(circuit, shots=4000, seed_simulator=1).result().get_counts()

    # Noiseless, 20 RXX(pi/2) gates are the identity and only 00 and 01 occur.
    assert counts.get("10", 0) + counts.get("11", 0) > 0
