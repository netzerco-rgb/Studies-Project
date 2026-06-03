import subprocess   # this library enables python to "run" an external progs
import os
import re

def run_isolated_agent(file_path):
    if not os.path.exists(file_path):
        print(f"Error: file {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()

    pattern = r'((?:CTLSPEC|LTLSPEC|INVARSPEC|SPEC)\s+NAME\s+(\w+)\s+:=[\s\S]*?;)'

    # keeps all specifications in a List which holds in evary posioton the entire specification text + it's name
    specs = re.findall(pattern, file_content)   

    if not specs:
        print("No named specifications found in the SMV file.")
        return

    # remove all specifications to create a clean "base model" of the SMV file
    base_model = re.sub(pattern, '', file_content)

    print(f"Agent detected {len(specs)} specifications. Running isolated tests...")
    
    passed_specs = 0
    total_specs = len(specs)
    
    # creating a temporary file in the same directory
    temp_file_path = os.path.join(os.path.dirname(file_path), 'temp_agent_run.smv')

    print("\n--- Agent Analysis Report ---")
    
    try:
        for idx, (full_spec_text, spec_name) in enumerate(specs, 1):     # idx holds the value of enumerate counter which initialized to 1
            # 1. writing the base model and just one specification to the temp file
            with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
                temp_file.write(base_model)
                temp_file.write("\n\n-- Injected by Agent for isolation:\n")
                temp_file.write(full_spec_text)
                temp_file.write("\n")

            # 2. run nuXmv on the temp file
            result = subprocess.run(
                ['nuXmv', temp_file_path], 
                capture_output=True, 
                text=True
            )
            output = result.stdout  # holds the entire terminal output who made ny nuXmv
            
            # 3. analyze the result and since there's only 1 spec, we just search for its result
            status = "UNKNOWN"
            if re.search(r'--\s+specification.*is\s+true', output, re.IGNORECASE):
                status = "TRUE"
                passed_specs += 1
            elif re.search(r'--\s+specification.*is\s+false', output, re.IGNORECASE):
                status = "FALSE"
            elif "error" in output.lower() or "syntax" in output.lower():
                status = "ERROR IN SMV CODE"
            
            print(f"[{idx}/{total_specs}] Spec: {spec_name} -> RESULT: {status}")

    except Exception as e:
        print("An error occurred during execution:", str(e))
        
    finally:
        # 4. cleaning up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    print("-------------------------------------------------")
    print(f"Summary: {passed_specs}/{total_specs} specifications are TRUE")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    smv_file_path = os.path.join(script_dir, 'SSP347_version_2.smv')
    run_isolated_agent(smv_file_path)