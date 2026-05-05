import sys
import os
from pathlib import Path

print(f"__file__: {__file__}")
print(f"os.path.dirname(__file__): {os.path.dirname(__file__)}")

# Current method in main.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
print(f"project_root (current): {project_root}")
print(f"project_root exists: {os.path.exists(project_root)}")

# Check for db directory
db_path = os.path.join(project_root, "db")
print(f"db_path: {db_path}")
print(f"db_path exists: {os.path.exists(db_path)}")

# List contents of project_root
if os.path.exists(project_root):
    print(f"\nContents of {project_root}:")
    for item in os.listdir(project_root):
        print(f"  - {item}")

# Check sys.path
print(f"\nsys.path:")
for p in sys.path:
    print(f"  - {p}")

# Test import
sys.path.insert(0, project_root)
try:
    import db.schemas
    print(f"\nSuccessfully imported db.schemas")
    print(f"db.schemas.__file__: {db.schemas.__file__}")
except ImportError as e:
    print(f"\nFailed to import db.schemas: {e}")
    
    # Try alternative path: one level up from backend directory
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    print(f"\nbackend_dir: {backend_dir}")
    parent_dir = os.path.dirname(backend_dir)
    print(f"parent_dir (alternative): {parent_dir}")
    print(f"parent_dir exists: {os.path.exists(parent_dir)}")
    
    db_path2 = os.path.join(parent_dir, "db")
    print(f"db_path2: {db_path2}")
    print(f"db_path2 exists: {os.path.exists(db_path2)}")
    
    if os.path.exists(db_path2):
        print(f"\nTrying with parent_dir in sys.path...")
        sys.path.insert(0, parent_dir)
        try:
            import db.schemas
            print(f"Successfully imported db.schemas with parent_dir")
        except ImportError as e2:
            print(f"Still failed: {e2}")