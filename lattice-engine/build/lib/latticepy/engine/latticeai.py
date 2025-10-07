import argparse
import os
import sys
import shutil
import platform
import toml
from pydantic import BaseModel, ValidationError
from typing import Optional


from LatticePy.interfaces.localdatabase import LocalDatabase, LocalDBModel


if platform.system() == "Windows":
    home_dir = os.path.join(os.environ["USERPROFILE"])
elif platform.system() == "Linux" or platform.system() == "Darwin":
    home_dir = os.path.expanduser("~")
else:
    print(f"Unsupported operating system: {platform.system()}")
    sys.exit()
lattice_folder = ".Lattice"
lattice_path = os.path.join(home_dir, lattice_folder)

if not os.path.exists(lattice_path):
    try:
        os.makedirs(lattice_path)
        print("Lattice Folder created successfully.")
    except OSError as e:
        print(f"Error: '{lattice_path}': {e}")
else:
    print(f"{lattice_path} exists.")



class ConfigModel(BaseModel):
    mode: str
    address: str
    port: int
    config_path: Optional[str] = f'{lattice_path}/config.toml'
    SOCKET: Optional[bool] = False
    DATABASE: LocalDBModel
    TOOL_SERVER: Optional[str] = None


class Config:

    def update(self, config):
        with open(config.config_path, "w") as config_file:
            config_file.write(toml.dumps(config.dict()))

    def load(self, config_path):
        with open(config_path, "r") as config_file:
            try:
                config = ConfigModel(**toml.load(config_file))
            except toml.TomlDecodeError as e:
                print(f"Error decoding TOML file: {e}")
                sys.exit(1)
            except ValidationError as e:
                print(f"Error validating configuration: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"Unexpected error: {e}")
                sys.exit(1)
            return config
            
class Client:
    @classmethod
    def run(cls, config):
        cls.config = config
        LocalDatabase(cls.config.DATABASE)
        import multiprocessing as mp
        from LatticePy.interfaces.webserver import startwebserver
        cls.webprocess = mp.Process(target=startwebserver, args=(cls.config.address, cls.config.port))
        cls.webprocess.start()

    def stop(self):
        pass

if __name__ == "__main__":
    # Example usage
    parser= argparse.ArgumentParser(description="LatticeAI Client")
    parser.add_argument("run", type=str, help="mode to run the client", choices=["interactive", "daemon"])
    parser.add_argument("--port", type=int, help="Port number to run the client on", default=44444)
    parser.add_argument("--address", type=str, help="Address to run the client on", default="localhost")
    parser.add_argument("--socket", action='store_true', help="to enable socket communication")
    parser.add_argument("--config", type=str, help="Path to the configuration file", default=None)
    args= parser.parse_args()
    
    if args.config:
        if os.path.exists(args.config):
            shutil.copy(args.config, os.path.join(lattice_path, "config.toml"))
        else:
            print("Config file not found")
            sys.exit(1)
    config_path = os.path.join(lattice_path, "config.toml")
    conf=Config()
    dbdata=LocalDBModel(name='localdb', url_path=lattice_path, db='sqlite3', password=None)
    if not os.path.exists(config_path):
        config=ConfigModel(mode=args.run, address=args.address, port=args.port, config_path=config_path, DATABASE=dbdata)
        conf.update(config)
    config=conf.load(config_path)
    client = Client.run(config)
