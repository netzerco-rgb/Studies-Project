# Formal Verification of Network-Based Biocomputation Circuits

This repository contains the Python code and formal models developed for the Computer Engineering final project **Using Hardware Tools to Test and Formally Verify Biological Circuits** (Project 418).

The project explores how hardware-oriented formal verification tools can be used to model and check **Network-Based Biocomputation (NBC)** circuits. These circuits represent computation as the movement of biological agents through interconnected channels. The implementations are software models of NBC behavior, rather than physical experiments.

## Problems and implementations

The repository is organized into two parts:

| Problem | Purpose | Verification tools | Documentation |
| --- | --- | --- | --- |
| **Subset Sum Problem (SSP)** | Model and verify the legal outputs of an SSP computation network | nuXmv, Z3 | [SSP README](./Subset%20Sum%20Problem/README.md) |
| **Hamiltonian Path** | Check whether a graph contains a path that visits every vertex exactly once, using two NBC-inspired encodings | nuXmv, Z3 | [Hamiltonian Path README](./Hamiltonian%20Path%20Problem/README.md) |

SSP is used as an initial case study. Hamiltonian Path extends the project with two modeling approaches—**Tree-Based routing** and **Coloring/Tagging-Based encoding**—each evaluated using both verification engines.

## Repository structure

```text
Studies-Project/
├── README.md
├── SSP/
│   ├── README.md
│   ├── dynamic_ssp_nuxmv.py
│   ├── ssp_agent_nuxmv_runner.py
│   ├── z3_dynamic_ssp.py
│   └── Z3_SSP_Dynamic _old.py       # Optional legacy version
└── Hamiltonian_Path/
    ├── README.md
    ├── dynamic_hamiltonian_tree_nuxmv.py
    ├── z3_dynamic_hamiltonian_tree.py
    ├── dynamic_hamilton_coloring_nuxmv.py
    ├── z3_dynamic_hamilton_coloring.py
    ├── HamiltonPath.smv             # Optional standalone example model
    └── graph*.txt                  # Graph instances / input files
```

*This is the intended layout after reorganizing the currently flat repository. Files shown as optional can be omitted if they are not part of the final code release.*

## Requirements

- Python 3.10 or newer
- **nuXmv** model checker (experiments used **2.1.0**)
- **Z3** SMT solver / `z3-solver` Python package (experiments used **4.16.0**)
- `psutil` for memory monitoring in the Hamiltonian Path scripts

Install the Python dependencies:

```bash
python -m pip install z3-solver psutil
```

Make sure `nuXmv` is installed and available on your system `PATH` before running nuXmv-based scripts.

## Getting started

Open the [SSP README](./Subset%20Sum%20Problem/README.md) or [Hamiltonian Path README](./Hamiltonian%20Path%20Problem/README.md) for the corresponding problem description, script explanations, input format, and run commands. Commands in the subfolder READMEs assume you are running them from the relevant folder.

## Scope

The project compares formal verification behavior and performance of different NBC-inspired models. Passing a formal check establishes the specified property **for the modeled instance and assumptions**; it does not by itself establish error-free behavior of a fabricated biological device.
