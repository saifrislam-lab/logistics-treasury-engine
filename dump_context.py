import os

# CONFIG
output_file = "PROJECT_FULL_CONTEXT.txt"
excluded_dirs = {'venv', '.git', '__pycache__', '.idea', '.vscode', 'node_modules'}
# We explicitly EXCLUDE .env to protect your keys
included_extensions = {'.py', '.sql', '.txt', '.md', '.json', '.csv'} 

def generate_context():
    with open(output_file, 'w', encoding='utf-8') as out:
        # 1. WRITE FILE TREE
        out.write("=== PROJECT STRUCTURE ===\n")
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * (level)
            out.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = " " * 4 * (level + 1)
            for f in files:
                out.write(f"{subindent}{f}\n")
        
        out.write("\n\n=== FILE CONTENTS ===\n")
        
        # 2. WRITE FILE CONTENTS
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                # Skip the dump script itself and the output file
                if file in ["dump_context.py", output_file]: 
                    continue
                    
                if any(file.endswith(ext) for ext in included_extensions):
                    path = os.path.join(root, file)
                    out.write(f"\n\n--- START OF FILE: {path} ---\n")
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            # Truncate huge CSVs to first 10 lines to save space
                            if file.endswith('.csv'):
                                head = [next(f) for _ in range(10)]
                                out.write("".join(head))
                                out.write("\n... [CSV TRUNCATED] ...")
                            else:
                                out.write(f.read())
                    except Exception as e:
                        out.write(f"[Error reading file: {e}]")
                    out.write(f"\n--- END OF FILE: {path} ---\n")

    print(f"✅ SUCCESS. Context saved to: {output_file}")
    print("👉 Please upload this file to the chat.")

if __name__ == "__main__":
    generate_context()