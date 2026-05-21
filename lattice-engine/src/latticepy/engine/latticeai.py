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
from pathlib import Path
import multiprocessing as mp

from latticepy.engine.core.pydanticmodels import ConfigModel, LocalDBModel

class MinimalFormatter(logging.Formatter):
    """A formatter that suppresses stack traces and stack info."""
    def formatException(self, ei):
        return ""
    def formatStack(self, stack_info):
        return ""

class MinimalFormatter(logging.Formatter):
    """A formatter that suppresses stack traces and stack info."""
    def formatException(self, ei):
        return ""
    def formatStack(self, stack_info):
        return ""


home_dir = str(Path.home())
lattice_folder = ".Lattice"
lattice_path = os.path.join(home_dir, lattice_folder, 'server')
os.makedirs(lattice_path, exist_ok=True)

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
    webprocess = None
    config = None

    @classmethod
    def run(cls, config):
        cls.config = config
        from latticepy.engine.core.localdatabase import LocalDatabase, initiaize_db
        lb=LocalDatabase()
        lb.initialize(cls.config.DATABASE)
        initiaize_db(lb)
        from latticepy.engine.core.webserver import startwebserver
        #LocalDatabase.drop(table_name='latticeagents')
        cls.webprocess = mp.Process(target=startwebserver, args=(cls.config.address, cls.config.port))
        cls.webprocess.start()
        try:
            cls.webprocess.join()
        except KeyboardInterrupt:
            cls.stop()

    @classmethod
    def stop(cls):
        if cls.webprocess and cls.webprocess.is_alive():
            logging.info("Shutting down the web server process gracefully...")
            if cls.webprocess.is_alive():
                cls.webprocess.terminate()
                cls.webprocess.join()

def main():
    parser= argparse.ArgumentParser(description="LatticeAI Client")
    subparsers = parser.add_subparsers(dest="command", required=True, help="mode to run the client")
    run_parser = subparsers.add_parser("run", help="Run the client")
    run_parser.add_argument("mode", type=str, nargs="?", help="mode to run the client", choices=["http", "daemon"], default='http')
    run_parser.add_argument("--port", type=int, help="Port number to run the client on", default=44444)
    run_parser.add_argument("--address", type=str, help="Address to run the client on", default="localhost")
    run_parser.add_argument("--config", type=str, nargs="?", help="Path to the configuration file", default=None)
    #run_parser.add_argument("--socket", action='store_true', help="to enable socket communication")
    db_parser = subparsers.add_parser("db", help="Run the client")
    db_parser.add_argument("--droptable", type=str, nargs="?", help="table name to drop", default=None)
    args= parser.parse_args()

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

    # example lattice-engine run http --port 44444 --address localhost
    
    
    
    dbdata=LocalDBModel(name='localdb', url_path=lattice_path, db='sqlite3', password=None)
    
    if args.command == "db":
        from latticepy.engine.core.localdatabase import LocalDatabase, initiaize_db
        lb=LocalDatabase()
        lb.initialize(dbdata)
        initiaize_db(lb)
        lb.drop(args.droptable)
        sys.exit(0)

    runtime_mode=args.mode
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.join(lattice_path, "config.toml")
    if not os.path.exists(config_path):
        logger.error(f"Provided config file does not exist: {config_path}")
        sys.exit(1)
    config=ConfigModel(mode=runtime_mode, address=args.address, port=args.port, config_path=config_path, DATABASE=dbdata)
    conf=Config()
    conf.update(config)
    conf.load(config_path)
    logger.info(f"Starting Lattice Client in {args.mode} mode")
    Client.run(config)
    

if __name__ == "__main__":
    main()