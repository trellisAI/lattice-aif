from typing import Optional, Dict
from pydantic import BaseModel
import os
import sys
import sqlite3
import logging
from contextlib import contextmanager

from latticepy.engine.core.pydanticmodels import LocalDBModel

logger = logging.getLogger(__name__)


class LocalDatabase:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalDatabase, cls).__new__(cls)
            cls._instance.db_path = os.environ.get("LATTICE_DB_PATH")
        return cls._instance


    def initialize(self, db: LocalDBModel):
        """
        Initialize the local database path. Call this once at startup.
        """
        if db.db == "sqlite3":
            self.db_path = os.path.join(db.url_path, db.name)
            os.environ["LATTICE_DB_PATH"] = self.db_path
            if not os.path.exists(self.db_path):
                try:
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                    # Just touch the file to ensure it can be created
                    with sqlite3.connect(self.db_path) as conn:
                        pass
                    logger.info(f"Database created at {self.db_path}")
                except OSError as e:
                    logger.error(f"Error creating database: {e}")
                    sys.exit(1)
            else:
                logger.info(f"Database exists at {self.db_path}")
        else:
            logger.error(f"Unsupported database type: {db.db}")
            sys.exit(1)
            
        self.db_name = db.name
        self.db_url = db.url_path

    @contextmanager
    def get_connection(self):
        """
        Context manager for yielding a database connection.
        """
        if getattr(self, 'db_path', None) is None:
            home_dir = str(os.path.expanduser('~'))
            config_path = os.path.join(home_dir, ".Lattice", "server", "config.toml")
            db_model = None
            
            if os.path.exists(config_path):
                import toml
                try:
                    with open(config_path, "r") as config_file:
                        config_data = toml.load(config_file)
                        if 'DATABASE' in config_data:
                            db_model = LocalDBModel(**config_data['DATABASE'])
                except Exception as e:
                    logger.error(f"Failed to load db config from {config_path}: {e}")
            
            if not db_model:
                lattice_path = os.path.join(home_dir, ".Lattice", 'server')
                db_model = LocalDBModel(name='localdb', url_path=lattice_path, db='sqlite3', password=None)
                
            self.initialize(db_model)
            # Make sure tables exist
            initiaize_db(self)
            
        if not self.db_path:
            raise ValueError("Database has not been initialized.")
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_tables(self, table_name: str, columns: Dict[str, str]):
        columns_str = ", ".join([f"{col} {typ}" for col, typ in columns.items()])
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        
        with self.get_connection() as conn:
            conn.execute(create_table_query)
            conn.commit()

    def drop(self, table_name: str):
        drop_query = f"DROP TABLE IF EXISTS {table_name}"
        with self.get_connection() as conn:
            conn.execute(drop_query)
            conn.commit()

def initiaize_db(db):
    db.create_tables(
    'latticeagents',
        {
        'id': 'TEXT PRIMARY KEY',
        'prompt': 'TEXT',
        'tools': 'TEXT',
        'details': 'TEXT'
        }
    )
    
    db.create_tables(
    'connections',
        {
            'id': 'TEXT PRIMARY KEY', 
            'source': 'TEXT', 
            'url': 'TEXT', 
            'api_key': 'TEXT',
            'model': 'TEXT',
            'details': 'TEXT'
        }
    )
    db.create_tables(
    'prompts',
        {
            'id': 'TEXT PRIMARY KEY',
            'prompt': 'TEXT'
        }
    )
    db.create_tables(
    'vectordb',
        {
            'id': 'TEXT PRIMARY KEY', 
            'db': 'TEXT', 'url': 'TEXT', 
            'password': 'TEXT', 
            'tablename': 'TEXT'
        }
        
    )

    db.create_tables(
    'toolservers',
        {
            'id': 'TEXT PRIMARY KEY',
            'url': 'TEXT',
            'details': 'TEXT'
        }   
)

