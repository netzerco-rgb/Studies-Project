import os
import re
import sys
import argparse
import subprocess
import time
import threading
import psutil
from typing import Dict, List


# Performance monitoring - 1ms sampling
def start_memory_monitor():
    python_process = psutil.Process(os.getpid())
    child_process = [None]
    peak_memory_kb = [0.0]
    stop_event = threading.Event()

    def sample_memory():
        total_bytes = 0

        try:
            total_bytes += python_process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        if child_process[0] is not None:
            try:
                total_bytes += child_process[0].memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        peak_memory_kb[0] = max(
            peak_memory_kb[0],
            total_bytes / 1024
        )

    def monitor():
        while not stop_event.is_set():
            sample_memory()
            stop_event.wait(0.001)

    start_time = time.perf_counter()
    sample_memory()

    thread = threading.Thread(
        target=monitor,
        daemon=True
    )
    thread.start()

    def stop_monitor():
        stop_event.set()
        thread.join()
        sample_memory()
        return (
            time.perf_counter() - start_time,
            peak_memory_kb[0]
        )

    return child_process, stop_monitor


# verifies that a vertex name has the valid format
def validate_vertex(vertex: str) -> None:
    if not re.fullmatch(r"v[1-9][0-9]*", vertex):
        raise ValueError(
            f"Invalid vertex name '{vertex}'. "
            "Vertices must use the format v1, v2, v3, ..."
        )


# converts a vertex name to its corresponding integer
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

            # undirected input graph
            graph_sets[u].add(v)
            graph_sets[v].add(u)

    if not graph_sets:
        raise ValueError(
            "The graph file does not contain any vertices."
        )

    graph = {}
    for vertex in sorted(graph_sets, key=vertex_number):
        graph[vertex] = sorted(
            graph_sets[vertex],
            key=vertex_number
        )

    return graph


def generate_tagging_smv(graph):
    """
    generates an SMV file for finding a Hamiltonian path using the tagging approach.
    graph - a dictionary representing the adjacency list of an undirected graph.
    """
    num_nodes = len(graph)
    max_step = num_nodes - 1

    # extract numbers from node names ('v1' -> 1) and sort them
    nodes = sorted([int(n.replace('v', '')) for n in graph.keys()])
    node_str_list = ", ".join(map(str, nodes))

    smv = "MODULE main\n\n"

    # ================== VAR Block ==================
    smv += "VAR\n"
    smv += f"  step : 0..{max_step};\n"
    smv += f"  curr_node : {{{node_str_list}}};\n\n"

    for n in nodes:
        smv += f"  visited_{n} : boolean;\n"

    # ================= ASSIGN Block ================
    smv += "\nASSIGN\n"
    smv += "  init(step) := 0;\n"
    smv += f"  init(curr_node) := {{{node_str_list}}};\n\n"

    # loop creates a specific tag for every vertex
    for n in nodes:
        smv += f"  init(visited_{n}) := (curr_node = {n});\n"

    # advancing the step counter
    smv += f"""
  next(step) := case
    step < {max_step} : step + 1;
    TRUE     : step;
  esac;
"""

    # routing the agent according to the graph topology
    smv += "\n  next(curr_node) := case\n"
    smv += f"    step = {max_step} : curr_node;\n"

    # loop creates the next possible moves of the agent from it's current position
    for node in sorted(graph.keys()):
        numeric_node = int(node.replace('v', ''))
        numeric_neighbors = sorted([int(neighbor.replace('v', '')) for neighbor in graph[node]])

        # handle isolated nodes
        if not numeric_neighbors:
            continue

        neighbors_str = ", ".join(map(str, numeric_neighbors))
        smv += f"    curr_node = {numeric_node} : {{{neighbors_str}}};\n"

    smv += "    TRUE : curr_node;\n  esac;\n\n"

    # updating the accumulated tags
    for n in nodes:
        smv += f"  next(visited_{n}) := (next(curr_node) = {n}) | visited_{n};\n"

    # ================ Specification ================
    visited_cond = " & ".join([f"visited_{n}" for n in nodes])
    full_cond = f"(step = {max_step} & {visited_cond})"

    smv += "\n-- Specification: extracting a hamiltonian path if one exists\n"
    smv += f"CTLSPEC !(EF {full_cond})\n"

    return smv


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hamiltonian Path Tagging (Coloring) model generator and verifier with Performance Metrics."
    )

    parser.add_argument(
        "graph_file",
        help="Path to the graph input txt file."
    )

    parser.add_argument(
        "--output",
        type=str,
        default="auto_generated_tagging_nbc.smv",
        help="Optional path for the generated SMV file."
    )

    args = parser.parse_args()

    # Start total execution time and memory monitoring
    child_process, stop_monitor = start_memory_monitor()

    try:
        # building the graph dictionary from the provided txt file
        G = read_graph(args.graph_file)

        # creates the SMV file
        final_code = generate_tagging_smv(G)
        file_name = args.output

        with open(file_name, "w", encoding="utf-8") as f:
            f.write(final_code)

        print(f"Success! Generated SMV for graph with {len(G)} nodes.")
        print(f"Saved to '{file_name}'.")
        print("-" * 40)
        print("Running nuXmv automatically...\n")

        try:
            process = subprocess.Popen(["nuXmv", file_name])
            child_process[0] = psutil.Process(process.pid)
            process.wait() # wait for nuXmv to finish
            child_process[0] = None

        except FileNotFoundError:
            print("Error: nuXmv command not be found.")
            sys.exit(1)

        # printing the performance report
        total_runtime, max_memory_usage_kb = stop_monitor()
        print("\n--- Performance Metrics ---")
        print(f"Execution Time: {total_runtime:.4f} seconds")
        print(f"Max Memory Usage (Python + nuXmv): {max_memory_usage_kb:.2f} KB")

    except (ValueError, FileNotFoundError) as e:
        print(f"\nError: {e}")
        sys.exit(1)
