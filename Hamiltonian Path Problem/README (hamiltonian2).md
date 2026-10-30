# Hamiltonian Path — Formal Verification

This folder contains code developed as part of the Computer Engineering final project **Using Hardware Tools to Test and Formally Verify Biological Circuits** (Project 418).

The project focuses on using formal hardware verification tools to model and verify network-based biocomputation (NBC) circuits. This implementation addresses the **Hamiltonian Path Problem**, which asks whether a graph contains a path that visits every vertex exactly once.

The code uses two NBC-inspired encoding approaches:

1. **Tree-Based routing**, which decomposes high-degree vertices into binary splitter chains.
2. **Coloring-Based encoding**, which represents the requirement that each vertex is visited only once.

Each approach is implemented with two formal verification tools: **nuXmv** and **Z3**. The implementations are software abstractions of NBC circuits, not physical biological devices.

[Back to the repository overview](../README.md)

## Contents

1. [Built With](#1-built-with)
2. [Setup and Requirements](#2-setup-and-requirements)
3. [Usage](#3-usage)
4. [Hamiltonian Path Modeling Approaches](#4-hamiltonian-path-modeling-approaches)
5. [Repository Files](#5-repository-files)
6. [Project Goal](#6-project-goal)
7. [Limitations](#7-limitations)
8. [Notes](#8-notes)

## 1. Built With

The project uses the following tools and technologies:

- **Python** — graph processing, dynamic model generation, verification execution, and performance measurement.
- **nuXmv** — symbolic model checking of generated SMV transition systems.
- **Z3 SMT Solver** — constraint-based verification and Hamiltonian path discovery.
- **psutil** — sampled process-memory monitoring in the benchmark scripts.

Both encoding approaches are available with both verification engines:

| Encoding approach | nuXmv | Z3 |
| --- | --- | --- |
| **Tree-Based** | `dynamic_hamiltonian_tree_nuxmv.py` | `z3_dynamic_hamiltonian_tree.py` |
| **Coloring-Based** | `dynamic_hamilton_coloring_nuxmv.py` | `z3_dynamic_hamilton_coloring.py` |

## 2. Setup and Requirements

Before running the scripts, make sure the following tools are installed:

- Python 3.10 or newer
- nuXmv (version **2.1.0** used in the project experiments)
- Z3 Python package (`z3-solver`; Z3 version **4.16.0** used in the experiments)
- `psutil` Python package
- Windows or Linux operating system

### Install Python dependencies

```bash
python -m pip install z3-solver psutil
```

### Install nuXmv

Install nuXmv and make sure its executable is accessible from the command line. For example, check it with:

```bash
nuXmv -h
```

If the command is not recognized, add the directory containing the nuXmv executable to the system `PATH`.


## 3. Usage

Run the commands below from the `Hamiltonian_Path` folder.

### Graph input

The scripts read a graph from a text file. A representative **undirected** example is:

```text
vertices: v1 v2 v3 v4
v1 v2
v1 v3
v1 v4
v2 v3
v3 v4
```

The first line declares the vertices, and each following line specifies an edge. Use the input format supported by the checked-in version of the scripts. Replace `graph.txt` in the examples below with the graph file you want to verify.

### Run the Tree-Based nuXmv version

```bash
python dynamic_hamiltonian_tree_nuxmv.py graph.txt
```

This script generates an SMV transition-system model that represents graph routing through binary splitter chains and runs nuXmv to check for a Hamiltonian path. The Tree-Based implementation can test possible starting vertices until it finds a valid path or exhausts the candidates.

### Run the Tree-Based Z3 version

```bash
python z3_dynamic_hamiltonian_tree.py graph.txt
```

This script represents the tree-routed graph using SMT constraints and checks whether a Hamiltonian path can be found while respecting the routing structure and original graph adjacency.

### Run the Coloring-Based nuXmv version

```bash
python dynamic_hamilton_coloring_nuxmv.py graph.txt
```

This script generates an SMV model that tracks vertex visits through state flags/tags and uses nuXmv to check whether all vertices can be visited exactly once along valid edges.

### Run the Coloring-Based Z3 version

```bash
python z3_dynamic_hamilton_coloring.py graph.txt
```

This script represents a candidate Hamiltonian path as a sequence of symbolic vertices. Z3 uses adjacency constraints to require a valid edge between consecutive vertices and the `Distinct` constraint to prevent revisiting a vertex.

### Understanding the results

For Hamiltonian Path, the result refers to **the existence of a valid path**, not whether an error was found in the model:

- **Path exists:** a Hamiltonian path satisfying the modeled constraints was found/reachable.
- **Path does not exist:** no such path exists within the checked graph/model.
- **Unknown or interrupted:** verification did not produce a conclusive result; this should not be treated as proof that a path does not exist.

In the Z3 path-existence formulation, `sat` means that a valid path exists, while `unsat` means that the constraints admit no valid Hamiltonian path. In nuXmv, a reachability property such as `EF(done)` is **true** when a completed Hamiltonian path is reachable. This differs from the SSP Z3 script, where `unsat` means no *invalid* computation path was found.

The benchmark implementations also report **Total Execution Time** and **Max Memory Usage** (sampled, in KB). For nuXmv, the measurement includes the Python runner and the nuXmv process; for Z3, it includes Python with Z3. The sampled maximum is an observed value, not an exact system-wide memory peak.

## 4. Hamiltonian Path Modeling Approaches

The Hamiltonian Path problem involves finding a path through a graph that visits every vertex exactly once. In this project, the graph is represented as a Network-Based Biocomputation (NBC) model, where agents move through connected vertices and routing junctions.

Two different encoding approaches were developed to represent and formally verify the Hamiltonian Path problem.

**Original input graph:**

![Original graph used for both Hamiltonian Path encodings](images/original_graph.png)

*The input graph has four vertices. Both approaches encode Hamiltonian paths in this same graph, but represent the routing and vertex-visit constraints differently.*

### 4.1 Tree-Based Approach

The Tree-Based approach converts graph vertices with multiple outgoing connections into chains of binary splitters, representing the routing decisions of biological agents in an NBC network.

For example, if a vertex is connected to three neighboring vertices, its outgoing connections are represented using a sequence of binary routing junctions rather than a single junction with three possible exits.

This introduces intermediate routing states (pseudo-vertices) that represent the agent's movement through the splitter chain. These states are part of the physical routing representation but do not count as additional logical vertices in the Hamiltonian Path.

A valid Hamiltonian Path must visit every original graph vertex exactly once while following legal connections through the routed network.

![Tree-Based network representation with valid Hamiltonian paths highlighted](images/tree_based_routing.png)

*Tree-Based encoding of the input graph. Filled nodes indicate split junctions, hollow nodes indicate pass junctions, and green nodes mark valid Hamiltonian exits. The pink and blue routes illustrate two valid Hamiltonian paths through the routed network.*

**Implementation:**

- **nuXmv:** Generates an SMV transition system containing the original vertices, intermediate splitter states, and transitions between them. The model checker verifies whether a completed Hamiltonian Path is reachable.
- **Z3:** Encodes the logical Hamiltonian Path constraints together with the physical routing constraints, verifying that a candidate path is valid in both representations.

### 4.2 Coloring-Based Approach

The Coloring-Based approach represents the graph directly, without introducing intermediate splitter states. Instead, vertex-visit constraints are used to prevent an agent from visiting the same vertex more than once.

Each move follows an existing edge in the graph. A valid Hamiltonian Path is found when all vertices have been visited exactly once.

![Coloring-Based layered network representation with valid Hamiltonian paths highlighted](images/coloring_based_network.png)

*Coloring-Based network representation of the same graph. Each layer represents a successive vertex selection, while the highlighted pink and blue routes show two valid Hamiltonian paths.*

**Implementation:**

- **nuXmv:** Uses Boolean visited flags (tags) to record which vertices have already been visited. The transition system prevents revisiting a previously visited vertex and checks whether all vertices can be reached in a valid sequence.
- **Z3:** Uses symbolic path variables and the `Distinct` constraint to ensure that every vertex is visited exactly once. Adjacency constraints ensure that consecutive vertices are connected by valid graph edges.

### 4.3 Comparison of the Approaches

The main difference between the approaches is how the graph and routing decisions are represented.

The Tree-Based approach explicitly models the binary routing structure of an NBC network, making the representation more closely related to the physical movement of biological agents. However, the additional intermediate states increase the complexity of the verification model.

The Coloring-Based approach uses a more direct representation of the graph, avoiding intermediate routing states while enforcing vertex-visit constraints.

Both approaches are implemented using nuXmv and Z3 to compare their formal verification performance, execution time, and memory usage.

## 5. Repository Files

### `dynamic_hamiltonian_tree_nuxmv.py`

Dynamically builds a **Tree-Based SMV model** for an input graph and runs the nuXmv model checker.

Main functionality:

- Reads a graph from a text file.
- Converts high-degree routing choices into chains of binary splitter states.
- Generates a corresponding SMV transition system.
- Checks reachability of a completed Hamiltonian path with nuXmv.
- Attempts different starting vertices when necessary.
- Reports the verification result and performance measurements.

Example:

```bash
python dynamic_hamiltonian_tree_nuxmv.py graph.txt
```

### `z3_dynamic_hamiltonian_tree.py`

Implements the **Tree-Based routing approach using Z3** rather than generating an SMV file.

Main functionality:

- Reads the graph and builds its tree-routed representation.
- Introduces intermediate routing states for splitter chains.
- Encodes logical path and physical-routing constraints.
- Checks whether the model admits a valid Hamiltonian path.
- Reports the result and performance measurements.

Example:

```bash
python z3_dynamic_hamiltonian_tree.py graph.txt
```

### `dynamic_hamilton_coloring_nuxmv.py`

Dynamically generates a **Coloring/Tagging-Based SMV model** and verifies it with nuXmv.

Main functionality:

- Reads an input graph.
- Models vertex-visit information with state flags/tags.
- Encodes legal movement between adjacent graph vertices.
- Prevents revisiting vertices in a candidate Hamiltonian path.
- Uses nuXmv to check whether a completed path is reachable.
- Reports the result and performance measurements.

Example:

```bash
python dynamic_hamilton_coloring_nuxmv.py graph.txt
```

### `z3_dynamic_hamilton_coloring.py`

Verifies the **Coloring-Based Hamiltonian Path model using Z3** without explicitly maintaining visited tags.

Main functionality:

- Reads the input graph.
- Creates symbolic variables representing the vertices along a candidate path.
- Applies adjacency constraints to consecutive vertices.
- Uses `Distinct` to ensure every vertex appears exactly once.
- Checks whether a Hamiltonian path exists.
- Reports the result and performance measurements.

Example:

```bash
python z3_dynamic_hamilton_coloring.py graph.txt
```

### Graph input files (`graph*.txt`)

Text files containing graph instances used for testing, including small examples, larger connected graphs, and an instance with no Hamiltonian path. The exact filenames depend on which test graphs are included in the repository.

### `HamiltonPath.smv` (optional)

An earlier standalone Hamiltonian Path model that may be retained as a small example of the nuXmv encoding.

## 6. Project Goal

The goal of this project is to apply formal hardware verification techniques to NBC-inspired representations of **NP-Complete problems**.

For Hamiltonian Path, the objective is to determine whether an input graph contains a path visiting all vertices exactly once, and to evaluate how different ways of representing the underlying computation affect the performance of the verification engine.

The project compares two dimensions:

1. **Verification engines:** nuXmv model checking versus Z3 SMT solving.
2. **Encoding approaches:** Tree-Based routing versus Coloring/Tagging-Based modeling.

### Example

For the graph:

```text
vertices: v1 v2 v3 v4
v1 v2
v2 v3
v3 v4
```

one Hamiltonian path is:

```text
v1 -> v2 -> v3 -> v4
```

A successful path-existence check establishes that such a sequence is possible in the specified graph and encoding. The experiments also compare verification time and memory usage across different graph instances.

## 7. Limitations

The current implementation has several practical limitations:

- Verification time and memory consumption depend on the number of vertices, connectivity, topology, and whether a Hamiltonian path exists.
- **Tree-Based routing** introduces intermediate states for splitter chains. These states represent routing structure rather than additional original graph vertices, and they can increase model complexity.
- **Coloring/Tagging-Based modeling** encodes the no-revisit condition more directly, but it still faces computational limitations on larger graphs.
- An `unknown` result or a manually interrupted execution is **inconclusive**; it is not evidence that the graph has no Hamiltonian path.
- The memory measurements are sampled process-memory values, not direct measurements of a physical NBC circuit.
- Successful verification establishes the specified property for the **formal model and assumptions**. It does not independently prove that a fabricated biological circuit would operate without routing or junction errors.

## 8. Notes

This Hamiltonian Path implementation extends the project's earlier **Subset Sum Problem (SSP)** case study. Both problems use nuXmv and Z3, but the verification conditions are not identical: the SSP Z3 implementation searches for an **invalid computation**, while the Hamiltonian Path implementations search for the **existence of a valid path**.

The experimental results showed that **Coloring-Based Z3** performed particularly well on larger tested satisfiable graphs, while performance varied by input topology, encoding, and verification engine. These observations apply to the evaluated instances and do not imply universal superiority of one tool or encoding.

For the SSP implementation and its commands, see the [SSP README](./Subset%20Sum%20Problem/README.md).