from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
import json


from latticepy.engine.interfaces.llminterface import llmClient
from latticepy.engine.core.localdatabase import LocalDatabase
from latticepy.engine.core.pydanticmodels import PromptModel, VectorDB, ConnectionModel, Model

import logging

logger = logging.getLogger(__name__)

db = LocalDatabase()


# --- Data Management Classes ---

class Data:
    data = {} 

    @classmethod
    def _get_tablename(cls):
        mapping = {
            "LlmConnections": "connections",
            "Promptlist": "prompts",
            "VectorDBlist": "vectordb",
            "LatticeTools": "latticetools",
        }
        # If the current class isn’t found in the mapping then use its lowercase name.
        return mapping.get(cls.__name__, cls.__name__.lower())

    @classmethod
    def refresh(cls):
        # Should be overridden in each subclass
        pass

    @classmethod
    def _get_data(cls):
        """
        Fetches data from the database and updates the class data attribute.
        This method should be overridden in subclasses to implement specific data fetching logic.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def listdown(cls):
        cls.refresh()  # get current data from DB
        return(cls.data.keys())
 
    @classmethod
    def list(cls):
        cls.refresh()
        """
        Returns a list of keys in the data dictionary.
        """ 

        return {key: cls.data[key].model_dump() for key in cls.data.keys()}

    @classmethod
    def get(cls, key) -> Optional[Any]:
        cls.refresh()
        if key in cls.data:
            return cls.data[key]
        logger.warning(f"Data {key} not found.")
        return None

    @classmethod
    def add(cls, key, value):
        cls.refresh()
        if key in cls.data:
            logger.warning(f"Data {key} already exists.")
            raise ValueError(f"Data {key} already exists.")
        try:
            with LocalDatabase().get_connection() as conn:
                table = cls._get_tablename()
                data_dict = value.dict()
                for key, value in data_dict.items():
                    if isinstance(value, dict):
                        data_dict[key] = json.dumps(value)
                columns = ", ".join(data_dict.keys())
                placeholders = ", ".join(["?"] * len(data_dict))
                sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                conn.execute(sql, tuple(data_dict.values()))
                conn.commit()
        except Exception as e:
            logger.error(f"Error adding data to database: {e}")
            raise  ValueError(f"Error adding data to database: {e}")
        logger.info(f"Data {key} added to database.")
        cls.refresh()

    @classmethod
    def delete(cls, key):
        logger.info(f"Deleting data with key: {key}")
        try:
            with LocalDatabase().get_connection() as conn:
                table = cls._get_tablename()
                sql = f"DELETE FROM {table} WHERE id = ?"
                logger.debug(sql)
                conn.execute(sql, (key,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error deleting data from database: {e}")
            return
        logger.info(f"Data {key} deleted from database.")
        cls.refresh()

    @classmethod
    def clear(cls):
        try:
            with LocalDatabase().get_connection() as conn:
                table = cls._get_tablename()
                sql = f"DELETE FROM {table}"
                conn.execute(sql)
                conn.commit()
        except Exception as e:
            logger.error(f"Error clearing data from database: {e}")
            return
        logger.info("All data cleared from database.")
        cls.refresh()

    #def update

# --interfaces for data management classes --
class LlmConnections(Data):
    @classmethod
    def refresh(cls):
        with LocalDatabase().get_connection() as conn:
            rows = conn.execute("SELECT * FROM connections").fetchall()
        dict_rows = [dict(row) for row in rows]
        cls.data = {record["id"]: ConnectionModel(**record) for record in dict_rows}

class Promptlist(Data):
    @classmethod
    def refresh(cls):
        with LocalDatabase().get_connection() as conn:
            rows = conn.execute("SELECT * FROM prompts").fetchall()
        cls.data = {record["id"]: PromptModel(**record) for record in rows}

class VectorDBlist(Data):
    @classmethod
    def refresh(cls):
        with LocalDatabase().get_connection() as conn:
            rows = conn.execute("SELECT * FROM vectordb").fetchall()
        cls.data = {record["id"]: VectorDB(**record) for record in rows}

class LLMmodels():
    MODELS: Dict[str, Model] = {}

    def __init__(self) -> None:
        # For each connection refresh the list so that we use the latest connection info
        self.connections = LlmConnections.list()
        logger.debug(self.connections)
        for connection in self.connections:
            connec = LlmConnections.get(connection)
            if not connec:
                logger.warning(f"Connection {connection} not found.")
                continue
            Client=llmClient.get_client(connec)
            models = Client.models()
            if models:
                for model in models:
                    print(model)
                    self.MODELS.update({model.get('name'):Model(**model)})


    def listdown(self):
        if self.MODELS:
            logger.debug(f"Available models:{self.MODELS.keys()}")
            return list(self.MODELS.keys())
        else:
            logger.info("No models available.")

    def list(self) -> Dict:
        """
        Returns a list of model names.
        """
        return self.MODELS

    def get(self, key):
        if key in self.MODELS:
            return self.MODELS[key]
        logger.warning(f"Model {key} not found.")
        return None
  
class Workflows:
        pass

class MCPClients:
        pass
