import sys
import subprocess
import time
import psutil

def generate_tagging_smv(graph):
    """
    Generates an SMV file for finding a Hamiltonian path using the tagging approach.
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
    # check if arguments were provided in the command line
    if len(sys.argv) < 2:
        print("Usage: python generate_smv.py <edge1> <edge2> ...")
        print("Example: python generate_smv.py v1-v2 v1-v3 v1-v4 v2-v3 v3-v4")
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
        
        # add undirected connections (avoid duplicates)
        if v not in G[u]: G[u].append(v)
        if u not in G[v]: G[v].append(u)

    # generate and save
    final_code = generate_tagging_smv(G)
    file_name = "auto_generated_tagging_nbc.smv"
    
    with open(file_name, "w") as f:
        f.write(final_code)
        
    print(f"Success! Generated SMV for graph with {len(G)} nodes.")
    print(f"Saved to '{file_name}'.")
    print("-" * 40)
    print("Running nuXmv automatically...\n")
    
    # execution mechanism and accurate performance measurement for the nuXmv process
    nuxmv_start_time = time.perf_counter()
    max_mem_bytes = 0
    
    try:
        # opening a separate process instead of passive waiting allows us to sample it
        process = subprocess.Popen(["nuXmv", file_name])
        p = psutil.Process(process.pid)
        
        # sampling loop - as long as the process is running, check its memory consumption
        while process.poll() is None:
            try:
                mem_info = p.memory_info()
                # pulling the most accurate data from Windows, or using the standard data on other systems
                current_mem = getattr(mem_info, 'peak_wset', mem_info.rss)
                if current_mem > max_mem_bytes:
                    max_mem_bytes = current_mem
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # if the process finished in this exact millisecond, the loop will stop
                break
            
            # minimal delay to avoid creating artificial load on the CPU
            time.sleep(0.001)
            
        # wait for the process to fully complete in case it hasn't completely closed yet
        process.wait()
        
    except FileNotFoundError:
        print("Error: nuXmv command not found. Please ensure it is added to your system PATH.")
        sys.exit(1)
        
    nuxmv_end_time = time.perf_counter()
    
    # printing the performance report in the exact required format
    print("\n--- Performance Metrics ---")
    print(f"Execution Time: {nuxmv_end_time - nuxmv_start_time:.4f} seconds")
    print(f"Max Memory Usage (nuXmv): {max_mem_bytes / 1024:.2f} KB")
