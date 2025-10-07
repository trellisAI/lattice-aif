from typing import Optional, Dict
from pydantic import BaseModel
import os
import sys
import sqlite3

class LocalDBModel(BaseModel):
    name: str
    db: Optional[str] = "sqlite3"
    url_path: str 
    password: Optional[str] = None

class LocalDatabase:
    def __init__(self, db: LocalDBModel):
        
        """
        Initialize the local database with a given path.
        """
        
        if db.db == "sqlite3":
            self.db_path = os.path.join(db.url_path, db.name)
            if not os.path.exists(self.db_path):
                try:
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                    sqlite3.connect(self.db_path).close()
                    print(f"Database created at {self.db_path}")
                except OSError as e:
                    print(f"Error creating database: {e}")
                    sys.exit(1)
            else:
                print(f"Database exists at {self.db_path}")
            os.environ["LATTICE_DB_PATH"] = self.db_path

        else:
            print(f"Unsupported database type: {db.db}")
            sys.exit(1)
        self.db_name = db.name
        self.db_url = db.url_path
        self.db_password = db.password

    @classmethod
    def new_db( cls, dbconfig: LocalDBModel):
        """
        Create a new local database at the specified path.
        """
        pass
    
    @staticmethod
    def connect():
        db_path=os.environ.get("LATTICE_DB_PATH")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        return cur
    
    @staticmethod
    def create_tables(table_name: str, columns: Dict[str, str]):
        columns_str = ", ".join([f"{col} {typ}" for col, typ in columns.items()])
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        cur = LocalDatabase.connect()
        cur.execute(create_table_query)
        cur.connection.commit()

    @staticmethod
    def drop(table_name: str):
        drop_query=f"DROP TABLE IF EXISTS {table_name}"
        cur = LocalDatabase.connect()
        cur.execute(drop_query)
        cur.connection.commit()


    def disconnect(self):
        """
        Disconnect from the local database.
        """
        pass