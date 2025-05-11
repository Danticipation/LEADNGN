import sys
import importlib
import os
import subprocess

print("Python path:", sys.path)

# Try to find the installed packages
try:
    output = subprocess.check_output(['python', '-m', 'pip', 'list'], text=True)
    print("\nInstalled packages (pip list):")
    print(output)
except Exception as e:
    print(f"Error running pip list: {e}")

# Check all site-packages directories
for path in sys.path:
    if 'site-packages' in path or 'dist-packages' in path:
        print(f"\nLooking in packages directory: {path}")
        
        # List directories in site-packages
        try:
            if os.path.exists(path):
                dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                mirror_related = [d for d in dirs if 'mirror' in d.lower()]
                print("Mirror-related directories:", mirror_related)
                
                # Check all files in the directory
                all_files = sorted(os.listdir(path))
                mirror_files = [f for f in all_files if 'mirror' in f.lower()]
                print("Mirror-related files:", mirror_files)
            else:
                print(f"Directory {path} does not exist")
        except Exception as e:
            print(f"Error listing directories: {e}")

# Check specific dot pythonlibs path
lib_path = '/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages'
if os.path.exists(lib_path):
    print(f"\nLooking in specific path: {lib_path}")
    try:
        all_files = sorted(os.listdir(lib_path))
        print("All files in .pythonlibs:", all_files[:20], "..." if len(all_files) > 20 else "")
    except Exception as e:
        print(f"Error listing .pythonlibs: {e}")