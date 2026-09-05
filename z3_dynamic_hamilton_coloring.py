import sys
from z3 import *

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
    # check if arguments were provided in the command line
    if len(sys.argv) < 2:
        print("Usage: python z3_hamiltonian.py <edge1> <edge2> ...")
        print("Example: python z3_hamiltonian.py v1-v2 v1-v3 v1-v4 v2-v3 v3-v4")
        sys.exit(1)

    # building the graph dictionary from command line arguments
    G = {}
    edges = sys.argv[1:]
    
    for edge in edges:
        if '-' not in edge:
            print(f"Error: Invalid edge format '{edge}'. Please use 'vX-vY' format.")
            sys.exit(1)
            
        u, v = edge.split('-')
        
        # initialize nodes if they don't exist and make sure that every vertex has a list
        if u not in G: G[u] = []
        if v not in G: G[v] = []
        
        # adding undirected connections (avoid duplicates)
        if v not in G[u]: G[u].append(v)
        if u not in G[v]: G[v].append(u)

    print(f"[*] Analyzing graph with {len(G)} nodes using Z3...")
    
    # initialize the Z3 model
    solver, path_vars = find_hamiltonian_path_z3(G)
    
    # check satisfiability of the constraints
    result = solver.check()
    
    if result == sat:
        m = solver.model()
        # extract the assigned values for each step from the Z3 model
        path_sequence = [str(m[path_vars[i]]) for i in range(len(G))]
        formatted_path = " -> ".join([f"v{node}" for node in path_sequence])
        print("\n[+] Hamiltonian Path Found!")
        print(f"    Path: {formatted_path}")
    elif result == unsat:
        print("\n[-] No Hamiltonian path exists in this graph.")
    else:
        print("\n[!] Solver failed to decide (unknown).")
