import sys
import os
import importlib
import pkgutil

# Try to add the mirrorbot module directory to path
pythonlibs_path = '/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages'
if os.path.exists(pythonlibs_path):
    if pythonlibs_path not in sys.path:
        sys.path.insert(0, pythonlibs_path)
    print(f"Added {pythonlibs_path} to Python path")

# Check if we can import mirrorbot now
try:
    import mirrorbot
    print("Successfully imported mirrorbot:", mirrorbot.__file__)
    print("Package dir:", dir(mirrorbot))
    
    # Check if key modules exist
    try:
        from mirrorbot import ChatBot
        print("ChatBot class exists!")
    except ImportError as e:
        print("Could not import ChatBot:", e)
    
    try:
        from mirrorbot.conversation import Statement
        print("Statement class exists!")
    except ImportError as e:
        print("Could not import Statement:", e)
        
    # List all modules in the package
    print("\nModules in mirrorbot package:")
    package = importlib.import_module("mirrorbot")
    for finder, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        print(f"- {name} ({'package' if ispkg else 'module'})")
        
except ImportError as e:
    print("Still could not import mirrorbot:", e)
    
    # Check if the module file exists
    module_path = os.path.join(pythonlibs_path, "mirrorbot.py")
    module_dir_path = os.path.join(pythonlibs_path, "mirrorbot")
    
    if os.path.exists(module_path):
        print(f"Module file exists: {module_path}")
    elif os.path.exists(module_dir_path):
        print(f"Module directory exists: {module_dir_path}")
        print("Contents:")
        for item in os.listdir(module_dir_path):
            print(f"- {item}")
    else:
        print("Could not find mirrorbot module file or directory")
        
        # Look for egg or dist-info
        dist_info_dir = os.path.join(pythonlibs_path, "mirrorbot-1.3.dist-info")
        if os.path.exists(dist_info_dir):
            print(f"Found dist-info directory: {dist_info_dir}")
            print("Contents:")
            for item in os.listdir(dist_info_dir):
                print(f"- {item}")
                
                # If it's a metadata file, print the contents
                if item == "METADATA":
                    metadata_path = os.path.join(dist_info_dir, item)
                    print("\nMetadata content:")
                    with open(metadata_path, "r") as f:
                        print(f.read())
                        
            # Check top_level.txt
            top_level_path = os.path.join(dist_info_dir, "top_level.txt")
            if os.path.exists(top_level_path):
                print("\nTop level content:")
                with open(top_level_path, "r") as f:
                    print(f.read())
                    
    # Let's check the assets directory which seems to have the mirror bot code
    print("\nExploring attached_assets directory:")
    attached_assets_dir = "attached_assets"
    if os.path.exists(attached_assets_dir):
        print(f"Directory exists: {attached_assets_dir}")
        print("Contents:")
        for item in os.listdir(attached_assets_dir):
            if not item.startswith('__pycache__'):
                print(f"- {item}")
                
        # Check init file
        init_file = os.path.join(attached_assets_dir, "__init__.py")
        if os.path.exists(init_file):
            print("\nContents of __init__.py:")
            with open(init_file, "r") as f:
                print(f.read())