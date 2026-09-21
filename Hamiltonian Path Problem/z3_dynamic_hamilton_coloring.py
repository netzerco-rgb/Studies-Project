import os
import re
import sys
import argparse
import time
import psutil
from typing import Dict, List
from z3 import *

# verifies that a vertex name has the  valid format
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


def find_hamiltonian_path_z3(graph):
    """
    finds a Hamiltonian path in an undirected graph using Z3.
    graph - a dictionary representing the adjacency list.
    """
    nodes = sorted([int(n.replace('v', '')) for n in graph.keys()])
    num_nodes = len(nodes)
    
    solver = Solver()
    
    # create integer variables for each step in the path
    path = [Int(f"step_{i}") for i in range(num_nodes)]
    
    # constraint 1 - every step must be a valid node from the graph
    for p in path:
        solver.add(Or([p == n for n in nodes]))
        
    # constraint 2 - all nodes in the path must be distinct (visit every node exactly once)
    solver.add(Distinct(*path))
    
    # constraint 3 - valid transitions according to the graph topology (edges)
    for i in range(num_nodes - 1):
        valid_transitions = []
        for u in graph:
            numeric_u = int(u.replace('v', ''))
            for v in graph[u]:
                numeric_v = int(v.replace('v', ''))
                # if step i is node u, step i+1 must be a neighboring node v
                valid_transitions.append(And(path[i] == numeric_u, path[i+1] == numeric_v))
        
        solver.add(Or(valid_transitions))
        
    return solver, path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hamiltonian Path finder using Z3 SMT solver with Performance Metrics."
    )
    
    parser.add_argument(
        "graph_file",
        help="Path to the graph input txt file."
    )
    
    args = parser.parse_args()

    try:
        # building the graph dictionary from the input txt file
        G = read_graph(args.graph_file)
        
        print(f"[*] Analyzing graph with {len(G)} nodes using Z3...")
        
        # initialize the Z3 model
        solver, path_vars = find_hamiltonian_path_z3(G)
        
        # execution mechanism and accurate performance measurement for Z3
        z3_start_time = time.perf_counter()
        
        # check satisfiability of the constraints
        result = solver.check()
        
        z3_end_time = time.perf_counter()
        
        # getting memory consumption of the current Python process running Z3 directly
        p = psutil.Process()
        mem_info = p.memory_info()
        # pulling the most accurate data from Windows, or using the standard data on other systems
        max_mem_bytes = getattr(mem_info, 'peak_wset', mem_info.rss)
        
        if result == sat:
            m = solver.model()
            # extracting the assigned values for each step from the Z3 model
            path_sequence = [str(m[path_vars[i]]) for i in range(len(G))]
            formatted_path = " -> ".join([f"v{node}" for node in path_sequence])
            print("\n[+] Hamiltonian Path Found!")
            print(f"    Path: {formatted_path}")
        elif result == unsat:
            print("\n[-] No Hamiltonian path exists in this graph.")
        else:
            print("\n[!] Solver failed to decide (unknown).")

        print("\n--- Performance Metrics ---")
        print(f"Execution Time: {z3_end_time - z3_start_time:.4f} seconds")
        print(f"Max Memory Usage (Z3): {max_mem_bytes / 1024:.2f} KB")

    except (ValueError, FileNotFoundError) as e:
        print(f"\nError: {e}")
        sys.exit(1)
