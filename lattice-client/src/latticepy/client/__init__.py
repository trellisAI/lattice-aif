import platform
import os
import sys

if platform.system() == "Windows":
    home_dir = os.path.join(os.environ["USERPROFILE"])
elif platform.system() == "Linux" or platform.system() == "Darwin":
    home_dir = os.path.expanduser("~")
else:
    print(f"Unsupported operating system: {platform.system()}")
    sys.exit()
lattice_folder = ".Lattice"
lattice_path = os.path.join(home_dir, lattice_folder, 'client')

if not os.path.exists(lattice_path):
    try:
        os.makedirs(lattice_path)
        print("Lattice Folder created successfully.")
    except OSError as e:
        print(f"Error: '{lattice_path}': {e}")
else:
    print(f"{lattice_path} exists.")

os.environ["LAT_CL_HOME_DIR"]=lattice_path