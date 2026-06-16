import os
import subprocess
import sys
import argparse
from typing import List

def run_nuxmv(smv_file_path: str) -> None:
    """
    Executes the nuXmv model checker on the provided SMV file.
    """
    # command to execute nuXmv in the command line
    command = ['nuXmv', smv_file_path]
    
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
        print("Error: 'nuXmv' executable not found. Verify it is added to the system's PATH.")
        sys.exit(1)


def generate_dynamic_ssp_smv(elements: List[int], output_filename: str = "dynamic_ssp.smv") -> str:
    """
    generates a dynamic SMV model for the subset sum problem based on a list of elements.
    """
    # input validation: elements must be a non-empty list of positive integers
    if not elements or any(e <= 0 for e in elements):
        raise ValueError("Error: Elements must be a non-empty list of positive integers.")

    # 1. calculating the maximum sum
    max_sum = sum(elements)
    
    # 2. calculating split rows (cumulative Sum)
    # for example, for [3, 4, 7] this will generate [3, 7, 14]
    splits = []
    current = 0
    for e in elements:
        current += e
        splits.append(current)
        
    # 3.calculating all possible valid subset sums
    valid_sums = {0}
    for e in elements:
        valid_sums.update({v + e for v in valid_sums})
        
    # 4. finding all invalid sums (everything not in the valid set)
    invalid_sums = set(range(max_sum + 1)) - valid_sums
    
    # 5. creating condition strings for the SMV code below that will match the specific problem
    splits_cond = " | ".join(f"(_row = {s})" for s in splits)
    valid_cond = " | ".join(f"(_column={s})" for s in sorted(valid_sums))
    invalid_cond = " | ".join(f"(_column={s})" for s in sorted(invalid_sums)) if invalid_sums else "FALSE"
    
    # 6. building the complete SMV code for the file: dynamic_ssp.smv
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
CTLSPEC NAME alway_right_path := AG ((_row=max_sum) -> (_sum & !_xsum));
"""

    # saving the generated code to a file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(smv_code)
        
    print(f"Successfully generated '{output_filename}' for elements: {elements}")
    print(f"Target Valid Sums: {sorted(valid_sums)}")
    
    return output_filename


if __name__ == "__main__":
    
    # setup the argument parser
    parser = argparse.ArgumentParser(
        description="Dynamic Subset Sum Problem (SSP) Model Generator and Verifier for nuXmv."
    )
    
    # define the 'elements' argument as a list of integers (nargs='+' means one or more arguments)
    parser.add_argument(
        'elements', 
        metavar='N', 
        type=int, 
        nargs='+',
        help='A list of positive integers representing the subset sum elements (separated by spaces).'
    )
    
    # parse the arguments from the command line
    args = parser.parse_args()
    
    try:
        # getting the directory of this code file and setting the output path (for the SMV file) by that
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, 'dynamic_ssp.smv')
        
        # generating the SMV file using the provided arguments from command line
        generate_dynamic_ssp_smv(args.elements, output_path)
        
        # automatically running nuXmv on the generated file
        run_nuxmv(output_path)
        
    except ValueError as e:
        # catching the validation error (e.g., if negative numbers were provided)
        print(e)
        sys.exit(1)
