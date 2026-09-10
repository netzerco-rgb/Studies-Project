import os
import re
import sys
import argparse
import time
from typing import Dict, List, Tuple

from z3 import (
    Solver,
    Int,
    Bool,
    And,
    Or,
    Not,
    sat,
    is_true
)


# constants
DOWN = 0
DIAG = 1
DEAD = 0
MID_NONE = 0


# verifies that a vertex name has the format v<number>, for example: v1, v2, v10.
def validate_vertex(vertex: str) -> None:
    if not re.fullmatch(r"v[1-9][0-9]*", vertex):
        raise ValueError(
            f"Invalid vertex name '{vertex}'. "
            "Vertices must use the format v1, v2, v3, ..."
        )

# converts a vertex name such as v4 to the integer 4
def vertex_number(vertex: str) -> int:
    return int(vertex[1:])

# read graph from file
def read_graph(file_path: str) -> Dict[str, List[str]]:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"Graph file '{file_path}' was not found."
        )

    graph_sets = {}
    with open(file_path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            # ignore empty lines and comments
            if not line:
                continue
            if line.startswith("#") or line.startswith("--"):
                continue
            # remove inline comments
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if not line:
                continue

            # optional vertices declaration, for example: vertices: v1 v2 v3 v4
            if line.lower().startswith("vertices:"):
                vertex_text = line.split(":", 1)[1]
                vertices = vertex_text.replace(",", " ").split()
                for vertex in vertices:
                    validate_vertex(vertex)
                    graph_sets.setdefault(vertex, set())
                continue

            # edge declaration, supports: v1 v2 or v1-v2 for edge between v1 and v2
            edge_line = line.replace("-", " ")
            parts = edge_line.split()

            if len(parts) != 2:
                raise ValueError(
                    f"Invalid graph format on line {line_number}: "
                    f"'{line}'\n"
                    "Expected an edge such as 'v1 v2'."
                )

            u, v = parts

            validate_vertex(u)
            validate_vertex(v)

            graph_sets.setdefault(u, set())
            graph_sets.setdefault(v, set())

            # undirected original graph
            graph_sets[u].add(v)
            graph_sets[v].add(u)

    if not graph_sets:
        raise ValueError(
            "The graph file does not contain any vertices."
        )

    # v1 is always the starting vertex
    if "v1" not in graph_sets:
        raise ValueError(
            "The graph must contain v1 because "
            "v1 is the fixed starting vertex."
        )

    graph = {}

    for vertex in sorted(graph_sets, key=vertex_number):
        graph[vertex] = sorted(
            graph_sets[vertex],
            key=vertex_number
        )

    return graph

# build routed graph
def build_routed_graph(
        graph: Dict[str, List[str]]
) -> Dict[str, List[str]]:

    routed_graph = {}

    """
    for initial vertex v1 returning to it can never be part of a 
    valid Hamiltonian path, so those return edges are removed.
    """
    for vertex, neighbors in graph.items():
        if vertex != "v1":
            routed_graph[vertex] = [
                neighbor
                for neighbor in neighbors
                if neighbor != "v1"
            ]

        else:
            routed_graph[vertex] = list(neighbors)

    return routed_graph



# Build intermediate splitters -> mid_pos
def build_mid_positions(
        nodes: List[str],
        routed_graph: Dict[str, List[str]]
) -> Tuple[List[str], Dict[str, int]]:

    mid_names = []

    for node in nodes:

        degree = len(routed_graph[node])
        # degree 3 -> one mid position | degree 4 -> two mid positions | etc.
        if degree > 2:
            for i in range(1, degree - 1):
                mid_names.append(
                    f"{node}_s{i}"
                )

    """"
    Z3 uses integer codes internally for mid positions, meaning:
    for v1 who has 3 edgest: (v1 -> v2, v3, v4)  the mid_pos will be kept as integer 0: (0, "v1_s1")
    and next in integer 1 etc. 
    """
    mid_codes = {
        name: index + 1
        for index, name in enumerate(mid_names)
    }
    return mid_names, mid_codes

""" 
maximum number of routed transitions from one vertex:
 degree 1 -> one transition
 degree 2 -> one transition
 degree 3 -> max two transitions
 degree 4 -> max three transitions
 etc.
"""
def route_cost(degree: int) -> int:
    if degree == 0:
        return 0
    return max(1, degree - 1)

# Z3 verification
def verify_hamiltonian_path_z3(

        graph: Dict[str, List[str]]
) -> None:

    nodes = sorted(
        graph.keys(),
        key=vertex_number
    )

    node_numbers = [
        vertex_number(node)
        for node in nodes
    ]

    num_nodes = len(nodes)

    routed_graph = build_routed_graph(graph)

    mid_names, mid_codes = build_mid_positions(
        nodes,
        routed_graph
    )

    #  decides how long the Z3 execution trace needs to be
    max_route_transitions = sum(
        route_cost(len(routed_graph[node]))
        for node in nodes
    )

    num_states = max_route_transitions + 1

    solver = Solver()

    # variables
    pos = [
        Int(f"pos_{t}")
        for t in range(num_states)
    ]

    mid_pos = [
        Int(f"mid_pos_{t}")
        for t in range(num_states)
    ]

    step_num = [
        Int(f"step_num_{t}")
        for t in range(num_states)
    ]

    direction = [
        Int(f"direction_{t}")
        for t in range(num_states)
    ]

    visited = {}

    for node in nodes:

        number = vertex_number(node)

        visited[number] = [
            Bool(f"visited_{number}_{t}")
            for t in range(num_states)
        ]

    # legal variable values
    allowed_pos_values = [DEAD] + node_numbers
    allowed_mid_values = [MID_NONE] + list(mid_codes.values())

    for t in range(num_states):
        solver.add(
            Or(*[
                pos[t] == value
                for value in allowed_pos_values
            ])
        )

        solver.add(
            Or(*[
                mid_pos[t] == value
                for value in allowed_mid_values
            ])
        )

        solver.add(
            And(
                step_num[t] >= 1,
                step_num[t] <= num_nodes
            )
        )

        solver.add(
            Or(
                direction[t] == DOWN,
                direction[t] == DIAG
            )
        )

    # Initial state
    solver.add(
        pos[0] == 1
    )

    solver.add(
        mid_pos[0] == MID_NONE
    )

    solver.add(
        step_num[0] == 1
    )

    solver.add(
        direction[0] == DOWN
    )

# sets only v1 as visited, the rest are not in the initial state [0]
    for node in nodes:
        number = vertex_number(node)
        if node == "v1":
            solver.add(
                visited[number][0]
            )
        else:
            solver.add(
                Not(visited[number][0])
            )

    # done condition
    def done_at(t: int):
        return And(
            step_num[t] == num_nodes,
            *[
                visited[vertex_number(node)][t]
                for node in nodes
            ]
        )


    # keep all visited tags unchanged
    def keep_visited(t: int):
        return [
            visited[vertex_number(node)][t + 1]
            ==
            visited[vertex_number(node)][t]
            for node in nodes
        ]

    # marks target vertex as visited
    def unchanged_visited_values(
            t: int,
            target: str
    ):
        target_number = vertex_number(target)
        updates = []
        for node in nodes:
            number = vertex_number(node)
            if number == target_number:
                updates.append(
                    visited[number][t + 1] == True
                )
            else:
                updates.append(
                    visited[number][t + 1]
                    ==
                    visited[number][t]
                )
        return updates


    # Transition relation
    for t in range(num_states - 1):
        cases = []

        # when at the end all vertices were visited and we stay in this state -win
        cases.append(
            And(
                done_at(t),
                pos[t + 1] == pos[t],
                mid_pos[t + 1] == mid_pos[t],
                step_num[t + 1] == step_num[t],
                direction[t + 1] == direction[t],

                *keep_visited(t)
            )
        )


        # when we reach a dead-end, and we stay in it - fail
        cases.append(
            And(
                pos[t] == DEAD,
                pos[t + 1] == DEAD,
                mid_pos[t + 1] == MID_NONE,
                step_num[t + 1] == step_num[t],
                direction[t + 1] == direction[t],

                *keep_visited(t)
            )
        )

        # transitions for each graph vertex
        for source in nodes:
            source_number = vertex_number(source)
            neighbors = routed_graph[source]
            degree = len(neighbors)

            # no legal move so next move is a dead end - fail
            if degree == 0:
                cases.append(
                    And(
                        Not(done_at(t)),
                        pos[t] == source_number,
                        mid_pos[t] == MID_NONE,
                        pos[t + 1] == DEAD,
                        mid_pos[t + 1] == MID_NONE,
                        step_num[t + 1] == step_num[t],
                        direction[t + 1] == direction[t],

                        *keep_visited(t)
                    )
                )
                continue

            # split branch that enters a vertex
            def add_target_cases(
                    source_mid_code: int,
                    target: str,
                    branch_direction: int
            ):
                target_number = vertex_number(target)

                # target has not been visited -> legal move
                cases.append(
                    And(
                        Not(done_at(t)),
                        pos[t] == source_number,
                        mid_pos[t] == source_mid_code,
                        Not(
                            visited[target_number][t]
                        ),
                        direction[t + 1] == branch_direction,
                        pos[t + 1] == target_number,
                        mid_pos[t + 1] == MID_NONE,
                        step_num[t + 1] == step_num[t] + 1,
                        *unchanged_visited_values(
                            t,
                            target
                        )
                    )
                )

                # target has been visited -> no legal move
                cases.append(
                    And(
                        Not(done_at(t)),
                        pos[t] == source_number,
                        mid_pos[t] == source_mid_code,
                        visited[target_number][t],
                        direction[t + 1] == branch_direction,
                        pos[t + 1] == DEAD,
                        mid_pos[t + 1] == MID_NONE,
                        step_num[t + 1] == step_num[t],

                        *keep_visited(t)
                    )
                )

            # degree 1 -> pass junction
            if degree == 1:
                target = neighbors[0]
                target_number = vertex_number(target)
                # unvisited target
                cases.append(
                    And(
                        Not(done_at(t)),
                        pos[t] == source_number,
                        mid_pos[t] == MID_NONE,

                        Not(
                            visited[target_number][t]
                        ),
                        direction[t + 1] == direction[t],
                        pos[t + 1] == target_number,
                        mid_pos[t + 1] == MID_NONE,
                        step_num[t + 1] == step_num[t] + 1,
                        *unchanged_visited_values(
                            t,
                            target
                        )
                    )
                )

                # visited target -> dead
                cases.append(
                    And(
                        Not(done_at(t)),
                        pos[t] == source_number,
                        mid_pos[t] == MID_NONE,
                        visited[target_number][t],
                        direction[t + 1] == direction[t],
                        pos[t + 1] == DEAD,
                        mid_pos[t + 1] == MID_NONE,
                        step_num[t + 1] == step_num[t],
                        *keep_visited(t)
                    )
                )
                continue

            # degree >= 2 -> binary split chain
            for i in range(degree - 1):

                # first split occurs directly at graph vertex
                if i == 0:
                    current_mid_code = MID_NONE

                else:
                    current_mid_name = (
                        f"{source}_s{i}"
                    )

                    current_mid_code = (
                        mid_codes[current_mid_name]
                    )

                # DOWN -> next graph neighbor
                down_target = neighbors[i]
                add_target_cases(
                    current_mid_code,
                    down_target,
                    DOWN
                )

                # DIAG1 -> final graph neighbor
                if i == degree - 2:
                    diag_target = neighbors[i + 1]
                    add_target_cases(
                        current_mid_code,
                        diag_target,
                        DIAG
                    )

                # DIAG2 -> next intermediate splitter
                else:
                    next_mid_name = (
                        f"{source}_s{i + 1}"
                    )

                    next_mid_code = (
                        mid_codes[next_mid_name]
                    )

                    cases.append(
                        And(
                            Not(done_at(t)),
                            pos[t] == source_number,
                            mid_pos[t] == current_mid_code,
                            direction[t + 1] == DIAG,
                            pos[t + 1] == source_number,
                            mid_pos[t + 1] == next_mid_code,
                            step_num[t + 1]== step_num[t],
                            *keep_visited(t)
                        )
                    )

        solver.add(
            Or(*cases)
        )

    # Hamiltonian Path must eventually reach done
    solver.add(
        Or(*[
            done_at(t)
            for t in range(num_states)
        ])
    )

    # Run Z3
    print("\n--- Z3 Verification ---")
    print(
        f"Number of vertices: {num_nodes}"
    )

    edge_count = sum(
        len(neighbors)
        for neighbors in graph.values()
    ) // 2

    print(
        f"Number of original graph edges: "
        f"{edge_count}"
    )

    print(
        f"Number of intermediate splitters: "
        f"{len(mid_names)}"
    )

    print(
        f"Maximum routed states checked: "
        f"{num_states}"
    )

    print(
        "Starting vertex: v1"
    )

    # Performance Metrics
    start_time = time.perf_counter()
    result = solver.check()
    end_time = time.perf_counter()
    stats = solver.statistics()
    try:
        peak_memory_mb = stats.get_key_value("max memory")
    except:
        peak_memory_mb = stats.get_key_value("memory")
    peak_memory_kb = peak_memory_mb * 1024


    # SAT - Hamiltonian Path exists
    if result == sat:
        model = solver.model()
        print("\nResult: SAT")
        print(
            "Hamiltonian Path exists."
        )

        hamiltonian_path = []
        routed_trace = []

        for t in range(num_states):
            pos_value = model.evaluate(
                pos[t],
                model_completion=True
            ).as_long()

            mid_value = model.evaluate(
                mid_pos[t],
                model_completion=True
            ).as_long()

            step_value = model.evaluate(
                step_num[t],
                model_completion=True
            ).as_long()

            direction_value = model.evaluate(
                direction[t],
                model_completion=True
            ).as_long()

            # convert position back to name
            if pos_value == DEAD:
                pos_name = "dead"
            else:
                pos_name = f"v{pos_value}"

            # convert mid-position back to name
            if mid_value == MID_NONE:
                mid_name = "none"
            else:
                mid_name = next(
                    name
                    for name, code
                    in mid_codes.items()
                    if code == mid_value
                )

            # direction name
            if direction_value == DOWN:
                direction_name = "down"
            else:
                direction_name = "diag"
            routed_trace.append(
                (
                    t,
                    pos_name,
                    mid_name,
                    step_value,
                    direction_name
                )
            )

            # add only actual graph vertices to the Hamiltonian Path
            if (
                pos_value != DEAD
                and mid_value == MID_NONE
                and (
                    not hamiltonian_path
                    or hamiltonian_path[-1]
                    != pos_name
                )
            ):
                hamiltonian_path.append(
                    pos_name
                )

            # stop printing once done was reached
            if is_true(
                model.evaluate(
                    done_at(t),
                    model_completion=True
                )
            ):
                break

        print(
            "\nHamiltonian Path: "
            + " -> ".join(
                hamiltonian_path
            )
        )

        print(
            "\n--- Routed NBC Trace ---"
        )

        for (
            state,
            pos_name,
            mid_name,
            step_value,
            direction_name
        ) in routed_trace:

            print(
                f"State {state}: "
                f"pos={pos_name}, "
                f"mid_pos={mid_name}, "
                f"step_num={step_value}, "
                f"direction={direction_name}"
            )

    # UNSAT - Hamiltonian Path exists
    else:
        print("\nResult: UNSAT")
        print(
            "No Hamiltonian Path starting from v1 exists."
        )
    print("\n--- Performance Metrics ---")
    print(f"Execution Time: {end_time - start_time:.4f} seconds")
    print(f"Max Memory Usage (Z3): {peak_memory_kb:.2f} KB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Dynamic tree-routed Hamiltonian Path "
            "verifier using Z3. "
            "The path always starts from v1."
        )
    )

    parser.add_argument(
        "graph_file",
        help="Path to the graph input file."
    )

    args = parser.parse_args()
    try:
        graph = read_graph(
            args.graph_file
        )
        print(
            "\n--- Original Graph Input ---"
        )
        for vertex, neighbors in graph.items():
            print(
                f"{vertex}: "
                f"{', '.join(neighbors) if neighbors else 'no neighbors'}"
            )
        verify_hamiltonian_path_z3(
            graph
        )

    except (
        ValueError,
        FileNotFoundError
    ) as e:
        print(
            f"\nError: {e}"
        )

        sys.exit(1)