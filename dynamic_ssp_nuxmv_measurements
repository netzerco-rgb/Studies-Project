import os
import subprocess
import sys
import argparse
import time
import psutil  # Required for memory measurement on Windows
from typing import List

# Attempt to import the resource module for memory measurement (supported natively on Linux/macOS)
try:
    import resource
except ImportError:
    resource = None

def run_nuxmv(smv_file_path: str) -> None:
    """
    Executes nuXmv and measures Execution Time and Peak Memory Usage (Cross-platform).
    """
    command = ['nuXmv', smv_file_path]
    print(f"\n--- Starting nuXmv Execution for {smv_file_path} ---")
    
    start_time = time.perf_counter()
    max_memory_usage = 0
    
    try:
        # Launch nuXmv as a subprocess
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wrap the process with psutil to monitor its resources
        psutil_process = psutil.Process(process.pid)
        
        # Continuously poll the memory usage while the process is running
        while process.poll() is None:
            try:
                mem_info = psutil_process.memory_info()
                # Update max_memory_usage if the current reading is higher
                if mem_info.rss > max_memory_usage:
                    max_memory_usage = mem_info.rss
            except psutil.NoSuchProcess:
                # Process finished between loop iterations
                break
            
            # Short sleep to prevent the while-loop from hogging the CPU
            time.sleep(0.01)
            
        # Wait for the process to fully complete and capture output
        stdout, stderr = process.communicate()
        end_time = time.perf_counter()
        
        print("\n--- nuXmv Execution Output ---")
        print(stdout)
        
        print("--- Performance Metrics ---")
        print(f"Execution Time: {end_time - start_time:.4f} seconds")
        print(f"Max Memory Usage (nuXmv): {max_memory_usage / 1024:.2f} KB")
        
        if process.returncode != 0:
            print(f"Error executing nuXmv. Exit code: {process.returncode}")
            print("--- Error Output ---")
            print(stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        print("Error: 'nuXmv' executable not found. Verify it is added to the system's PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


def generate_dynamic_ssp_smv(elements: List[int], output_filename: str = "dynamic_ssp.smv") -> str:
    """
    Generates a dynamic SMV model for the Subset Sum Problem (SSP) based on a given list of elements.
    """
    # Input validation: elements must be a non-empty list of positive integers
    if not elements or any(e <= 0 for e in elements):
        raise ValueError("Error: Elements must be a non-empty list of positive integers.")

    # 1. Calculate the maximum possible sum (if all elements are chosen)
    max_sum = sum(elements)
    
    # 2. Calculate the split rows (Cumulative Sums)
    # For example, for the input [3, 4, 7], this will generate [3, 7, 14]
    splits = []
    current = 0
    for e in elements:
        current += e
        splits.append(current)
        
    # 3. Calculate all possible valid subset sums using a mathematical set
    valid_sums = {0}
    for e in elements:
        valid_sums.update({v + e for v in valid_sums})
        
    # 4. Find all invalid sums (any sum from 0 to max_sum that is not in the valid_sums set)
    invalid_sums = set(range(max_sum + 1)) - valid_sums
    
    # 5. Create condition strings for the SMV code to dynamically match the specific problem instance
    splits_cond = " | ".join(f"(_row = {s})" for s in splits)
    valid_cond = " | ".join(f"(_column={s})" for s in sorted(valid_sums))
    invalid_cond = " | ".join(f"(_column={s})" for s in sorted(invalid_sums)) if invalid_sums else "FALSE"
    
    # 6. Build the complete SMV logic string
    smv_code = f"""MODULE main

VAR
  _row : 0..{max_sum};
  _column : 0..{max_sum};
  direction : {{down, diag}};
  junction_type : {{split, pass}};

DEFINE
  max_sum := {max_sum};
  is_split_row := {splits_cond};
  
  _sum := {valid_cond};
  _xsum := {invalid_cond};

ASSIGN
  init(_row) := 0;
  init(_column) := 0;
  init(direction) := down;
  init(junction_type) := split;

  next(_row) := 
    case
      _row = max_sum : 0;
      TRUE : _row + 1;
    esac;

  next(direction) :=
    case
      _row = max_sum : down;
      junction_type = split : {{down, diag}};
      junction_type = pass  : direction;
      TRUE : direction;
    esac;

  next(_column) :=
    case
      _row = max_sum : 0;
      junction_type = split & next(direction) = down : _column;
      junction_type = split & next(direction) = diag : (_column < max_sum ? _column + 1 : 0);
      junction_type = pass & direction = down : _column;
      junction_type = pass & direction = diag : (_column < max_sum ? _column + 1 : 0);
      TRUE : _column;
    esac;

  next(junction_type) :=
    case
      _row = max_sum : split;
      next(is_split_row) : split;
      TRUE    : pass;
    esac;

-- Specifications
CTLSPEC NAME always_right_path := AG ((_row=max_sum) -> (_sum & !_xsum));
"""

    # Save the generated code string to the specified SMV file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(smv_code)
        
    print(f"Successfully generated '{output_filename}' for elements: {elements}")
    print(f"Target Valid Sums: {sorted(valid_sums)}")
    
    return output_filename


if __name__ == "__main__":
    
    # Setup the argument parser for command-line execution
    parser = argparse.ArgumentParser(
        description="Dynamic Subset Sum Problem (SSP) Model Generator and Verifier for nuXmv."
    )
    
    # Define the 'elements' argument as a list of integers (nargs='+' means one or more arguments)
    parser.add_argument(
        'elements', 
        metavar='N', 
        type=int, 
        nargs='+',
        help='A list of positive integers representing the subset sum elements (separated by spaces).'
    )
    
    # Parse the arguments from the command line
    args = parser.parse_args()
    
    try:
        # Get the directory of this code file to set the absolute output path for the SMV file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, 'dynamic_ssp.smv')
        
        # Generate the SMV file using the parsed arguments
        generate_dynamic_ssp_smv(args.elements, output_path)
        
        # Automatically run nuXmv on the generated file to test and measure performance
        run_nuxmv(output_path)
        
    except ValueError as e:
        # Catch validation errors (e.g., if negative numbers were provided)
        print(e)
        sys.exit(1)
