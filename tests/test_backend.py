import math

import pytest
from qiskit import QuantumCircuit, transpile

from fakepiastq import BASIS_GATES, FakePiast


def _ghz_counts(backend):
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.measure_all()
    transpiled = transpile(circuit, backend, seed_transpiler=1)
    assert set(transpiled.count_ops()) <= {*BASIS_GATES, "measure", "barrier"}
    return backend.run(transpiled, shots=4000, seed_simulator=1).result().get_counts()


def test_has_device_size_and_native_gates(calibration):
    backend = FakePiast.from_dict(calibration)
    assert backend.num_qubits == 20
    assert set(BASIS_GATES) <= set(backend.target.operation_names)
    assert "cx" not in backend.target.operation_names


def test_runs_noisy_circuit(calibration):
    counts = _ghz_counts(FakePiast.from_dict(calibration))
    ideal = counts.get("000", 0) + counts.get("111", 0)
    assert 0.8 * 4000 < ideal < 4000


def test_file_and_dict_give_the_same_backend(calibration_path, calibration):
    from_file = FakePiast.from_file(calibration_path)
    from_dict = FakePiast.from_dict(calibration)
    assert isinstance(from_file, FakePiast)
    assert _ghz_counts(from_file) == _ghz_counts(from_dict)


def test_from_file_accepts_a_string_path(calibration_path):
    assert FakePiast.from_file(str(calibration_path)).num_qubits == 20


def test_calibration_values_are_used(calibration):
    calibration["vendor"]["characterisation"]["spam_fidelity_lower_bound"] = 50.0

    circuit = QuantumCircuit(1)
    circuit.measure_all()
    job = FakePiast.from_dict(calibration).run(circuit, shots=4000, seed_simulator=1)
    ones = job.result().get_counts().get("1", 0)
    assert math.isclose(ones / 4000, 0.5, abs_tol=0.05)


def test_options_are_forwarded(calibration_path, calibration):
    for backend in (
        FakePiast.from_file(calibration_path, method="density_matrix"),
        FakePiast.from_dict(calibration, method="density_matrix"),
    ):
        assert backend.options.method == "density_matrix"


def test_rejects_circuits_wider_than_the_device(calibration):
    circuit = QuantumCircuit(21)
    circuit.measure_all()
    with pytest.raises(Exception):
        transpile(circuit, FakePiast.from_dict(calibration))
