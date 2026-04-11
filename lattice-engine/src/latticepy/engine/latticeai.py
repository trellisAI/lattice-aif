import argparse
import os
import sys
import shutil
import platform
import toml
import logging
from logging.handlers import TimedRotatingFileHandler
from pydantic import BaseModel, ValidationError
from typing import Optional

class MinimalFormatter(logging.Formatter):
    """A formatter that suppresses stack traces and stack info."""
    def formatException(self, ei):
        return ""
    def formatStack(self, stack_info):
        return ""


from latticepy.engine.services.localdatabase import LocalDatabase, LocalDBModel


if platform.system() == "Windows":
    home_dir = os.path.join(os.environ["USERPROFILE"])
elif platform.system() == "Linux" or platform.system() == "Darwin":
    home_dir = os.path.expanduser("~")
else:
    print(f"Unsupported operating system: {platform.system()}")
    sys.exit()
lattice_folder = ".Lattice"
lattice_path = os.path.join(home_dir, lattice_folder, 'server')

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
                logging.error(f"Error decoding TOML file: {e}")
                sys.exit(1)
            except ValidationError as e:
                logging.error(f"Error validating configuration: {e}")
                sys.exit(1)
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                sys.exit(1)
            return config
            
class Client:
    @classmethod
    def run(cls, config):
        cls.config = config
        LocalDatabase(cls.config.DATABASE)
        os.environ["LATTICE_DB_PATH"] = os.path.join(cls.config.DATABASE.url_path, cls.config.DATABASE.name)
        #LocalDatabase.drop(table_name='latticeagents')
        import multiprocessing as mp
        from latticepy.engine.services.webserver import startwebserver
        cls.webprocess = mp.Process(target=startwebserver, args=(cls.config.address, cls.config.port))
        cls.webprocess.start()

    def stop(self):
        pass


def main():
    parser= argparse.ArgumentParser(description="LatticeAI Client")
    parser.add_argument("run", type=str, help="mode to run the client", choices=["web", "daemon"], default='web')
    parser.add_argument("--port", type=int, help="Port number to run the client on", default=44444)
    parser.add_argument("--address", type=str, help="Address to run the client on", default="localhost")
    parser.add_argument("--socket", action='store_true', help="to enable socket communication")
    parser.add_argument("--config", type=str, help="Path to the configuration file", default=None)  
    args= parser.parse_args()
    # Configure logging
    log_dir = os.path.join(home_dir, lattice_folder, 'engine', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'lattice.log')

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers if any to avoid duplication
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # File Handler - All levels with daily rotation
    file_handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=7)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(file_handler)

    # Console Handler - Error and Warnings only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(MinimalFormatter("%(message)s"))
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)

    runtime_mode=args.run
    if args.config:
        if os.path.exists(args.config):
            shutil.copy(args.config, os.path.join(lattice_path, "config.toml"))
        else:
            logger.error("Config file not found")
            sys.exit(1)
    config_path = os.path.join(lattice_path, "config.toml")
    conf=Config()
    dbdata=LocalDBModel(name='localdb', url_path=lattice_path, db='sqlite3', password=None)
    
    if not os.path.exists(config_path):
        config=ConfigModel(mode=runtime_mode, address=args.address, port=args.port, config_path=config_path, DATABASE=dbdata)
        conf.update(config)
    config=conf.load(config_path)
    logger.info(f"Starting Lattice Client in {runtime_mode} mode")
    Client.run(config)

if __name__ == "__main__":
    main()