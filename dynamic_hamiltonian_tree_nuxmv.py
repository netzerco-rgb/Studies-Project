import os
import re
import sys
import argparse
import subprocess
from typing import Dict, List

"""
Reads an undirected graph from "graph.text" file, using the following format:

    vertices: v1 v2 v3 v4

    v1 v2
    v1 v3
    v1 v4
    v2 v3
    v3 v4

The vertices line is optional, but recommended because it
allows isolated vertices to be included in the graph.
"""

def run_nuxmv(smv_file_path: str) -> None:
    # command to execute nuXmv in the command line
    command = ["nuXmv", smv_file_path]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        # print the standard output
        print("\n--- nuXmv Execution Output ---")
        print(result.stdout)

    # handle cases where nuXmv was executed and print it's original error message
    except subprocess.CalledProcessError as e:
        print(f"Error executing nuXmv. Exit code: {e.returncode}")
        print("--- Error Output ---")
        print(e.stderr)
        sys.exit(1)

    # handle cases where nuXmv executable is not found by the OS
    except FileNotFoundError:
        print(
            "Error: 'nuXmv' executable not found. "
            "Verify that nuXmv is installed and added to the system PATH."
        )
        sys.exit(1)

# verifies that a vertex name has the format v<number>, for example: v1, v2, v10.
def validate_vertex(vertex: str) -> None:
    if not re.fullmatch(r"v[1-9][0-9]*", vertex):
        raise ValueError(
            f"Invalid vertex name '{vertex}'. "
            "Vertices must use the format v1, v2, v3, ..."
        )

# converts a vertex name such as v4 to the integer 4.
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

            # Optional vertices declaration, for example: vertices: v1 v2 v3 v4
            if line.lower().startswith("vertices:"):

                vertex_text = line.split(":", 1)[1]
                vertices = vertex_text.replace(",", " ").split()

                for vertex in vertices:
                    validate_vertex(vertex)
                    graph_sets.setdefault(vertex, set())

                continue

            # Edge declaration, supports: v1 v2 or v1-v2 for edge between v1 and v2
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

            # undirected input graph
            graph_sets[u].add(v)
            graph_sets[v].add(u)

    if not graph_sets:
        raise ValueError(
            "The graph file does not contain any vertices."
        )

    # v1 is always the starting vertex
    if "v1" not in graph_sets:
        raise ValueError(
            "The graph must contain v1 because v1 is the fixed starting vertex."
        )

    graph = {}

    for vertex in sorted(graph_sets, key=vertex_number):

        graph[vertex] = sorted(
            graph_sets[vertex],
            key=vertex_number
        )

    return graph

"""
for initial vertex v1 returning to it can never be part of a 
valid Hamiltonian path, so those return edges are removed.
"""
def build_routed_graph(
        graph: Dict[str, List[str]]
) -> Dict[str, List[str]]:

    routed_graph = {}

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

# generate dynamic Hamiltonian SMV model
def generate_dynamic_hamiltonian_smv(
        graph: Dict[str, List[str]],
        output_filename: str
) -> str:

    nodes = sorted(
        graph.keys(),
        key=vertex_number
    )

    num_nodes = len(nodes)
    routed_graph = build_routed_graph(graph)
    mid_positions = []

    for node in nodes:
        degree = len(routed_graph[node])
        if degree > 2:
            for i in range(1, degree - 1):
                mid_positions.append(
                    f"{node}_s{i}"
                )

    # VAR
    smv = "MODULE main\n\n"

    smv += "VAR\n"
    pos_values = ", ".join(nodes + ["dead"])

    smv += f"  pos : {{{pos_values}}};\n"

    if mid_positions:
        mid_values = ", ".join(
            ["none"] + mid_positions
        )
    else:
        # nuXmv requires more than one possible value
        # for mid_pos to remain a state variable
        mid_values = "none, unused"

    smv += f"  mid_pos : {{{mid_values}}};\n"
    smv += f"  step_num : 1..{num_nodes};\n"
    smv += "  direction : {down, diag};\n"

    for node in nodes:

        number = vertex_number(node)

        smv += (
            f"  visited_{number} : boolean;\n"
        )

    # DEFINE
    smv += "\nDEFINE\n"

    visited_conditions = [
        f"visited_{vertex_number(node)}"
        for node in nodes
    ]

    all_visited = " & ".join(
        visited_conditions
    )

    smv += (
        f"  done := "
        f"(step_num = {num_nodes} & {all_visited});\n"
    )

    split_conditions = []
    for node in nodes:
        degree = len(routed_graph[node])
        # if a split of 2
        if degree >= 2:
            split_conditions.append(
                f"(pos = {node} & mid_pos = none)"
            )
            # additional splitters
            if degree > 2:
                for i in range(1, degree - 1):

                    split_conditions.append(
                        f"(pos = {node} & "
                        f"mid_pos = {node}_s{i})"
                    )

    if split_conditions:
        smv += "  is_split_junction :=\n    "
        smv += " |\n    ".join(
            split_conditions
        )
        smv += ";\n\n"
    else:
        smv += (
            "  is_split_junction := FALSE;\n\n"
        )

    pass_conditions = []
    for node in nodes:
        if len(routed_graph[node]) == 1:
            pass_conditions.append(
                f"(pos = {node} & mid_pos = none)"
            )

    if pass_conditions:
        smv += "  is_pass_junction :=\n    "
        smv += " |\n    ".join(
            pass_conditions
        )
        smv += ";\n\n"

    else:
        smv += (
            "  is_pass_junction := FALSE;\n\n"
        )

    # agent is currently at a real graph vertex
    smv += (
        "  at_graph_vertex := "
        "mid_pos = none & pos != dead;\n\n"
    )


    # legal unvisited neighbor exists
    legal_conditions = []
    for node in nodes:
        neighbors = routed_graph[node]

        if not neighbors:
            continue

        unvisited_conditions = [
            f"!visited_{vertex_number(neighbor)}"
            for neighbor in neighbors
        ]

        neighbor_condition = " | ".join(
            unvisited_conditions
        )

        legal_conditions.append(
            f"(pos = {node} & "
            f"({neighbor_condition}))"
        )

    if legal_conditions:
        smv += (
            "  legal_move_exists := "
            "at_graph_vertex &\n    (\n      "
        )
        smv += " |\n      ".join(
            legal_conditions
        )
        smv += "\n    );\n\n"

    else:
        smv += (
            "  legal_move_exists := FALSE;\n\n"
        )

    smv += (
        "  no_legal_move := "
        "!done & at_graph_vertex & "
        "!legal_move_exists;\n"
    )

    # ASSIGN
    smv += "\nASSIGN\n"

    # v1 is always the initial graph vertex
    smv += "  init(pos) := v1;\n"
    smv += "  init(mid_pos) := none;\n"
    smv += "  init(step_num) := 1;\n"
    smv += "  init(direction) := down;\n"

    for node in nodes:
        number = vertex_number(node)
        if node == "v1":
            smv += (
                f"  init(visited_{number}) := TRUE;\n"
            )

        else:
            smv += (
                f"  init(visited_{number}) := FALSE;\n"
            )

    smv += "\n  next(direction) :=\n"
    smv += "  case\n"
    smv += (
        "    done : direction;\n"
    )
    smv += (
        "    pos = dead : direction;\n"
    )
    smv += (
        "    is_split_junction : {down, diag};\n"
    )
    smv += (
        "    is_pass_junction : direction;\n"
    )
    smv += (
        "    TRUE : direction;\n"
    )
    smv += "  esac;\n"

    # TRANS
    transitions = []

    # visited tags
    def visited_updates(
            target=None
    ) -> List[str]:

        updates = []
        for graph_node in nodes:
            number = vertex_number(
                graph_node
            )
            if graph_node == target:
                updates.append(
                    f"next(visited_{number}) = TRUE"
                )
            else:
                updates.append(
                    f"next(visited_{number}) = "
                    f"visited_{number}"
                )
        return updates

    # when at the end all vertices were visited and we stay in this state -win
    conditions = [
        "done",
        "next(direction) = direction",
        "next(pos) = pos",
        "next(mid_pos) = mid_pos",
        "next(step_num) = step_num"
    ]
    conditions.extend(
        visited_updates()
    )
    transitions.append(
        "(\n    " +
        " &\n    ".join(conditions) +
        "\n  )"
    )


    # when we reach a dead end and we stay in it - fail
    conditions = [
        "pos = dead",
        "next(direction) = direction",
        "next(pos) = dead",
        "next(mid_pos) = none",
        "next(step_num) = step_num"
    ]
    conditions.extend(
        visited_updates()
    )
    transitions.append(
        "(\n    " +
        " &\n    ".join(conditions) +
        "\n  )"
    )

    # no legal move so next move is a dead end - fail
    conditions = [
        "no_legal_move",
        "next(direction) = direction",
        "next(pos) = dead",
        "next(mid_pos) = none",
        "next(step_num) = step_num"
    ]
    conditions.extend(
        visited_updates()
    )
    transitions.append(
        "(\n    " +
        " &\n    ".join(conditions) +
        "\n  )"
    )

    # successful move to graph vertex
    def add_vertex_move(
            source: str,
            source_mid: str,
            target: str,
            branch_direction: str,
            is_pass: bool = False
    ) -> None:

        target_number = vertex_number(
            target
        )
        if is_pass:
            direction_condition = (
                "next(direction) = direction"
            )
        else:
            direction_condition = (
                f"next(direction) = "
                f"{branch_direction}"
            )

        # target has NOT been visited -> legal move
        conditions = [
            f"step_num < {num_nodes}",
            f"pos = {source}",
            f"mid_pos = {source_mid}",
            f"!visited_{target_number}",
            direction_condition,
            f"next(pos) = {target}",
            "next(mid_pos) = none",
            "next(step_num) = step_num + 1"
        ]
        conditions.extend(
            visited_updates(target)
        )
        transitions.append(
            "(\n    " +
            " &\n    ".join(conditions) +
            "\n  )"
        )

        # target already visited -> dead
        conditions = [
            f"step_num < {num_nodes}",
            f"pos = {source}",
            f"mid_pos = {source_mid}",
            f"visited_{target_number}",
            direction_condition,
            "next(pos) = dead",
            "next(mid_pos) = none",
            "next(step_num) = step_num"
        ]
        conditions.extend(
            visited_updates()
        )
        transitions.append(
            "(\n    " +
            " &\n    ".join(conditions) +
            "\n  )"
        )

    # move to intermediate splitter
    def add_mid_move(
            source: str,
            source_mid: str,
            target_mid: str
    ) -> None:

        conditions = [
            f"step_num < {num_nodes}",
            f"pos = {source}",
            f"mid_pos = {source_mid}",
            "next(direction) = diag",
            f"next(pos) = {source}",
            f"next(mid_pos) = {target_mid}",
            "next(step_num) = step_num"
        ]
        conditions.extend(
            visited_updates()
        )
        transitions.append(
            "(\n    " +
            " &\n    ".join(conditions) +
            "\n  )"
        )

    # generate routing for every graph vertex
    for node in nodes:
        neighbors = routed_graph[node]
        degree = len(neighbors)
        # no neighbors -> no_legal_move handles this case
        if degree == 0:
            continue

        # 1 neighbor -> pass junction
        if degree == 1:
            add_vertex_move(
                source=node,
                source_mid="none",
                target=neighbors[0],
                branch_direction="down",
                is_pass=True
            )
            continue

        """
        2 or more neighbors -> binary splitter chain
        
        Example degree 3 for v1 -> v2, v3, v4:
        v1
         down -> neighbor 1
         diag -> v1_s1
        
        v1_s1
         down -> neighbor 2
         diag -> neighbor 3
        
        """
        for i in range(degree - 1):
            if i == 0:
                current_mid = "none"
            else:
                current_mid = f"{node}_s{i}"
            # down always leads to the next graph neighbor
            down_target = neighbors[i]
            add_vertex_move(
                source=node,
                source_mid=current_mid,
                target=down_target,
                branch_direction="down"
            )

            # diagonal reaches final neighbor
            if i == degree - 2:
                diag_target = neighbors[i + 1]
                add_vertex_move(
                    source=node,
                    source_mid=current_mid,
                    target=diag_target,
                    branch_direction="diag"
                )

            # otherwise diagonal reaches another splitter
            else:
                next_mid = f"{node}_s{i + 1}"
                add_mid_move(
                    source=node,
                    source_mid=current_mid,
                    target_mid=next_mid
                )

    # TRANS relation
    smv += "\nTRANS\n  "
    smv += "\n\n  |\n\n  ".join(
        transitions
    )

    smv += ";\n"


    # CTL specifications
    smv += "\n"
    smv += "-- Hamiltonian Path specifications\n"

    smv += (
        "CTLSPEC NAME exists_hamiltonian_path := "
        "EF(done)\n"
    )

    # Used to display a Hamiltonian path as a counterexample when one exists.
    smv += (
        "CTLSPEC NAME no_hamiltonian_path := "
        "AG(!done)\n"
    )

    # save generated SMV model
    with open(
        output_filename,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(smv)

    # print information
    print("\n--- Model Generation ---")
    print(
        f"Successfully generated '{output_filename}'."
    )
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
        f"{len(mid_positions)}"
    )
    print("Starting vertex: v1")
    return output_filename


# MAIN
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Dynamic Tree-Routed Hamiltonian Path "
            "model generator and verifier for nuXmv. "
            "The path always starts from v1."
        )
    )

    parser.add_argument(
        "graph_file",
        help="Path to the graph input file."
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path for the generated SMV file."
    )

    args = parser.parse_args()

    try:

        graph = read_graph(
            args.graph_file
        )

        print("\n--- Original Graph Input ---")

        for vertex, neighbors in graph.items():
            print(
                f"{vertex}: "
                f"{', '.join(neighbors) if neighbors else 'no neighbors'}"
            )

        if args.output is None:
            script_dir = os.path.dirname(
                os.path.abspath(__file__)
            )

            output_path = os.path.join(
                script_dir,
                "dynamic_tree.smv"
            )

        else:
            output_path = os.path.abspath(
                args.output
            )

        generate_dynamic_hamiltonian_smv(
            graph,
            output_path
        )

        print("\n" + "-" * 50)
        print("Running nuXmv automatically...")
        print("-" * 50)

        run_nuxmv(
            output_path
        )

    except (
        ValueError,
        FileNotFoundError
    ) as e:

        print(f"\nError: {e}")
        sys.exit(1)