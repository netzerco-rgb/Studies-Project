import subprocess
import sys
import os

def run_nuxmv(smv_file_path):
    # command to execute nuXmv in the command line
    command = ['nuXmv', smv_file_path]
    
    try:
        # execute the command and capture standard output and error streams
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # print the standard output
        print("--- nuXmv Execution Output ---")
        print(result.stdout)
        
        # handle cases where nuXmv was executed and print it's original error message
    except subprocess.CalledProcessError as e:
        print(f"Error executing nuXmv. Exit code: {e.returncode}")
        print("--- Error Output ---")
        print(e.stderr)
        sys.exit(1)
        
    except FileNotFoundError:
        # handle cases where nuXmv executable is not found by the OS
        print("Error: 'nuXmv' executable not found.")
        print("Verify that nuXmv is installed and added to the system's PATH.")
        sys.exit(1)

if __name__ == "__main__":
    # get the path of the directory containing this python file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # dynamically join the directory path with the SMV file name to create a full path
    model_path = os.path.join(script_dir, 'SSP347_version_2.smv')
    
    run_nuxmv(model_path)
