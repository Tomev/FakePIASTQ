# PIAST-Q noise model: assumptions and limitations

`fake_piastq_noise_model()` builds a Qiskit Aer `NoiseModel` from the
calibration snapshot in `docs/callibration/piastq_2026-09-24.json`. This
document records what the model contains, what was assumed to build it, and
what it cannot represent.

In short: the model predicts average-case circuit fidelity about as well as the
published two-qubit fidelity allows. It is not qubit-accurate beyond the
single-qubit gates.

## What the model contains

| Instruction | Noise | Source in the calibration data |
|---|---|---|
| `r` (1Q) | Thermal relaxation over 31 µs, then depolarizing noise topping the total up to the reported fidelity. Different for each qubit. | `single_qubit_gate_fidelity`, `t1_s`, `t2_coherence_time_s`, `single_qubit_gate_duration_micros` |
| `rxx` (2Q) | The same construction over 508 µs. Identical for every pair. | `mean_two_qubit_gate_fidelity`, `t1_s`, `t2_coherence_time_s`, `two_qubit_gate_duration_micros` |
| `measure` | Symmetric bit-flip readout error, 0.37 %. Identical for every qubit. | `spam_fidelity_lower_bound` |
| `rz` | None. | Not in the data (see assumptions). |

Dephasing is not a separate channel. It enters through T2 as part of thermal
relaxation.

## Assumptions

These are not stated in the calibration files. They were supplied or agreed
while building the model.

1. **Native gates are `r`, `rz` and `rxx`.** This is the usual AQT gate set.
2. **Connectivity is all-to-all**, as for any AQT ion trap. The two-qubit
   error is therefore attached to `rxx` on every pair.
3. **Reported fidelities are fidelities of the native gates**, and they are
   read as average gate fidelity, which is Qiskit's convention for gate error.
4. **`rz` is virtual**, a frame update with no duration and no error.
5. **Relaxation is toward the ground state.** No temperature or excited-state
   population is published, so it is taken as zero.
6. **Gate errors are split the way `NoiseModel.from_backend` splits them.**
   Thermal relaxation is applied for the gate's duration, and depolarizing
   noise fills the gap up to the reported error.
7. **All SPAM error is placed on measurement.** The single SPAM figure covers
   preparation and measurement together. Reset is error-free.

## Limitations from the calibration data

1. **One two-qubit error for all 190 pairs.** Only a chain average is
   published, 97.24 ± 0.91 %. The model cannot tell good pairs from bad ones.
   This error dominates every circuit and is known only to about a third of
   its value, which bounds the accuracy of the whole model.
2. **Coarse readout error.** One number is used for all qubits, with equal
   0→1 and 1→0 flip probabilities. The figure is a vendor lower bound on
   fidelity, so the model is slightly pessimistic here.
3. **Depolarizing by assumption.** Fidelities give the size of each error but
   not its type. Coherent over-rotation and any dephasing beyond T2 are folded
   into depolarizing noise.
4. **Register-wide T1 and T2.** One value of each is published for the whole
   chain, so relaxation is the same on every qubit.
5. **Two qubits are modelled as noisier than reported.** Relaxation alone over
   a 31 µs gate gives an infidelity of 1.76×10⁻⁴. That exceeds the reported
   error of Q10 (1.0×10⁻⁴) and Q9 (1.7×10⁻⁴). Depolarizing noise cannot be
   negative, so both sit at 1.76×10⁻⁴. This suggests the published T2 is an
   idle figure that does not fully apply during gates. The overshoot is under
   10⁻⁴ per gate, small next to the two-qubit error of 2.76×10⁻².

## Deliberately left out

1. **Idle noise.** Qubits that wait while other gates run accumulate no error.
   On this device the effect could be large: if gates execute one at a time,
   a spectator ion idles through every other gate, and 20 `rxx` gates take
   about 10 ms against a T2 of 60 ms. The calibration data does not say
   whether gates run sequentially or in parallel, so this was excluded rather
   than guessed.
2. **Crosstalk.** The calibration file contains a measured 20×20 directed
   crosstalk matrix (nearest neighbours 3.04 %, distant ions 0.069 %). It is
   not used, for the reason given in the next section.

## Limitations of Qiskit's `NoiseModel`

These hold regardless of how good the calibration data is.

1. **Errors act only on the qubits of the instruction they are attached to.**
   `NoiseModel` offers `add_quantum_error`, `add_all_qubit_quantum_error` and
   the two readout equivalents, and nothing else. A gate on qubit 3 cannot
   disturb qubit 4. Crosstalk is exactly that kind of error, so the measured
   crosstalk matrix has no place to go. Using it would need something outside
   `NoiseModel`, such as a custom transpiler pass that inserts explicit error
   instructions on spectator qubits.
2. **Idle qubits get no noise unless the circuit says so.** Noise is triggered
   by instructions. Idle errors appear only if the circuit is scheduled and
   contains `delay` instructions with an error attached. Qiskit's scheduling
   passes assume gates on disjoint qubits run in parallel, which may not match
   an ion trap.
3. **Errors are keyed by gate name, not by gate parameters.** `rxx(θ)` gets
   the same error for every angle, and `r(θ, φ)` likewise. A smaller rotation
   is modelled as being as noisy as a full one.
4. **Errors are independent and memoryless.** Each error is a fixed channel
   applied at its gate. There is no drift over a run, no dependence on circuit
   depth (for example from motional heating), and no correlation between
   errors on different gates.
5. **Readout errors are classical.** A `ReadoutError` flips recorded bits with
   given probabilities. It does not change the quantum state, so it cannot
   represent a faulty mid-circuit measurement acting on the qubits that
   continue.
6. **No leakage.** Every channel acts within the qubit subspace.

## Notes on the calibration files

- The crosstalk matrix diagonal uses bare `NaN`. Python's `json` module
  accepts this, but strict JSON parsers reject it.
- The PDF card labels Q12 as the best single-qubit gate and Q3 as the worst.
  In the JSON they are Q10 (99.990 %) and Q19 (99.920 %). The values plotted
  on the card are correct; the qubit labels are not.
