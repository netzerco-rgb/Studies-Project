# Formal Verification of Network-Based Biocomputation Circuits

This repository contains code developed as part of a final project in Computer Engineering.

The project focuses on using formal verification tools to model and verify network-based biocomputation circuits. The main goal is to encode an NP-Complete problem as a network-based biocomputation model and verify that the encoding behaves correctly according to its formal definition.

The current implementation focuses on the Subset Sum Problem (SSP). The code generates and verifies SSP models using two verification approaches:

1. Model checking with nuXmv
2. SMT-based verification with Z3

The project is inspired by the use of state-of-the-art formal hardware verification tools for analyzing biological computation models.

## Contents

1. [Built With](#1-built-with)
2. [Setup and Requirements](#2-setup-and-requirements)
3. [Usage](#3-usage)
4. [Repository Files](#4-repository-files)
5. [Project Goal](#5-project-goal)
6. [Limitations](#6-limitations)
7. [Notes](#7-notes)

## 1. Built With

The project uses the following tools and technologies:

- Python
- nuXmv
- Z3 SMT Solver

## 2. Setup and Requirements

Before running the scripts, make sure the following tools are installed:

- Python 3.10 or newer
- nuXmv
- Z3 Python package
- Windows or Linux operating system

### Install Z3

For the Z3-based verification script, install the Z3 Python package:

```bash
pip install z3-solver
```

### Install nuXmv

For the nuXmv-based scripts, make sure nuXmv is installed and accessible from the command line.

You can check this by running:

```bash
nuXmv
```

If the command is not recognized, nuXmv should be added to the system PATH.

## 3. Usage

The scripts are run from the command line.

### Run the dynamic nuXmv version

```bash
python SSP_Dynamic.py 3 4 7
```

This generates a dynamic SMV model for the given SSP instance and runs nuXmv on the generated file.

For the input:

```text
3 4 7
```

the valid subset sums are:

```text
0, 3, 4, 7, 10, 11, 14
```

The script verifies that every complete computation path ends in a valid subset-sum column.

### Run the Z3 version

```bash
python Z3_SSP_Dynamic.py 3 4 7
```

This models the SSP computation as a bounded transition system and uses Z3 to check whether a bad computation path exists.

The meaning of the result is:

- `SAT`: a counterexample exists, meaning there is a complete computation path ending in an invalid column.
- `UNSAT`: no bad complete path exists, meaning the encoding is correct for the checked instance.

### Track Specific Points in the Z3 Computation

The Z3 script also supports tracking specific points in the computation path.

Example:

```bash
python Z3_SSP_Dynamic.py 3 4 7 --track 3,1 7,3 14,8
```

This checks whether the computation path passes through the selected row-column points.

## 4. Repository Files

### `Improved_Agent.py`

This script is used to run a nuXmv model from Python.

It executes nuXmv from the command line and prints the verification output. This is useful for connecting generated or existing SMV files with the nuXmv model checker automatically.

Main functionality:

- Builds the path to an SMV model file
- Runs nuXmv
- Prints the output
- Reports execution errors if nuXmv fails

### `SSP_Dynamic.py`

This script dynamically generates an SMV model for the Subset Sum Problem.

The input is a list of positive integers. The script calculates the network structure and creates a corresponding SMV model that represents the SSP computation.

Main functionality:

- Reads SSP elements from the command line
- Validates the input
- Calculates the maximum possible sum
- Calculates valid subset sums
- Finds invalid output columns
- Generates a dynamic SMV model
- Runs nuXmv on the generated model
- Verifies that the model reaches only legal SSP outputs

Example:

```bash
python SSP_Dynamic.py 3 4 7
```

### `Z3_SSP_Dynamic.py`

This script verifies the SSP network encoding using the Z3 SMT solver.

Instead of generating an SMV file, the script creates a symbolic transition system directly in Z3. It then checks whether there exists a complete path that violates the expected SSP behavior.

Main functionality:

- Reads SSP elements from the command line
- Calculates valid and invalid subset sums
- Defines the transition system
- Encodes the verification condition
- Searches for a counterexample
- Prints a trace if a bad path is found
- Supports tracking selected points in the computation

Example:

```bash
python Z3_SSP_Dynamic.py 3 4 7
```

With tracked points:

```bash
python Z3_SSP_Dynamic.py 3 4 7 --track 3,1 7,3 14,8
```

## 5. Project Goal

The goal of this project is to formally verify network-based biocomputation circuit encodings of NP-Complete problems.

The current implementation focuses on the Subset Sum Problem, which is NP-Complete. The SSP instance is encoded as a network-based computation model, and formal verification is used to check that the model produces only valid outputs.

The verification checks whether a complete computation path can end in an invalid result. If no such path exists, the encoding is considered correct for the checked instance.

This project demonstrates how formal hardware verification methods can be applied to biological computation models, allowing correctness checks of network encodings using tools such as nuXmv and Z3.

### Example

For the SSP input:

```text
3 4 7
```

the possible subset sums are:

```text
0, 3, 4, 7, 10, 11, 14
```

The verification goal is to prove that the computation can only end in one of these valid columns, and never in an invalid output column.

## 6. Limitations

The current implementation has several practical limitations:

- The scripts currently support only positive integer inputs.
- There is no fixed hard-coded maximum number of SSP elements, but larger inputs may significantly increase runtime and memory usage.
- The number of possible subset sums can grow exponentially with the number of input elements.
- The size of the generated model depends on the maximum possible sum, calculated as the sum of all input elements.
- In the Z3 implementation, the default path length is equal to the maximum sum, so large input values can make the solver much slower.

## 7. Notes

This repository is currently focused on the SSP case. Future extensions may include additional NP-Complete problems and larger generated instances.
