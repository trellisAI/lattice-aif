from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


from latticepy.engine.interfaces.llminterface import llmClient
from latticepy.engine.services.localdatabase import LocalDatabase



# --- Initialize Local Database ---
LocalDatabase.create_tables(
    'connections',
    {'id': 'TEXT PRIMARY KEY', 'source': 'TEXT', 'url': 'TEXT', 'api_key': 'TEXT'}
)
LocalDatabase.create_tables(
    'prompts',
    {'id': 'TEXT PRIMARY KEY', 'prompt': 'TEXT'}
)
LocalDatabase.create_tables(
    'vectordb',
    {'id': 'TEXT PRIMARY KEY', 'db': 'TEXT', 'url': 'TEXT', 'password': 'TEXT', 'tablename': 'TEXT'}   # renamed column
)
LocalDatabase.create_tables(
    'latticetools',
    {'id': 'TEXT PRIMARY KEY', 'description': 'TEXT', 'toollist': 'TEXT'}
)

# --- Data Models ---

class PromptModel(BaseModel):
    id: str
    prompt: str

class VectorDB(BaseModel):
    id: str
    db: str = Field(default='postgres')  # default value for db
    url: str
    password: str
    tablename: str   # renamed from 'table'

class ConnectionModel(BaseModel):
    id: str
    source: Optional[str] = 'ollama'
    url: str
    api_key: Optional[str]

class Model(BaseModel):
    name: str
    model: str
    source: ConnectionModel
    details: Optional[Dict[str, Any]] = None

class ToolsModel(BaseModel):
    id: str
    description: Optional[str] = None
    toollist: str = Field(default='[]')  # default to empty list as string

    def __str__(self):
        return f"Tool(id={self.id}, description={self.description})"


# --- Data Management Classes ---

class Data:
    data = {}  # mapping id -> object

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
        print(f"Data {key} not found.")
        return None

    @classmethod
    def add(cls, key, value):
        cls.refresh()
        if key in cls.data:
            print(f"Data {key} already exists.")
            raise ValueError(f"Data {key} already exists.")
        try:
            conn = LocalDatabase.connect()
            table = cls._get_tablename()
            # Assume the model can be converted to dict
            data_dict = value.dict()
            columns = ", ".join(data_dict.keys())
            placeholders = ", ".join(["?"] * len(data_dict))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            conn.execute(sql, tuple(data_dict.values()))
            conn.connection.commit()
        except Exception as e:
            print(f"Error adding data to database: {e}")
            raise  ValueError(f"Error adding data to database: {e}")
        print(f"Data {key} added to database.")
        cls.refresh()

    @classmethod
    def delete(cls, key):
        print(f"Deleting data with key: {key}")
        try:
            conn = LocalDatabase.connect()
            table = cls._get_tablename()
            sql = f"DELETE FROM {table} WHERE id = ?"
            print(sql)
            conn.execute(sql, (key,))
            conn.connection.commit()
        except Exception as e:
            print(f"Error deleting data from database: {e}")
            return
        print(f"Data {key} deleted from database.")
        cls.refresh()

    @classmethod
    def clear(cls):
        try:
            conn = LocalDatabase.connect()
            table = cls._get_tablename()
            sql = f"DELETE FROM {table}"
            conn.execute(sql)
            conn.connection.commit()
        except Exception as e:
            print(f"Error clearing data from database: {e}")
            return
        print("All data cleared from database.")
        cls.refresh()

    #def update

# --interfaces for data management classes --
class LlmConnections(Data):
    @classmethod
    def refresh(cls):
        rows = LocalDatabase.connect().execute("SELECT * FROM connections").fetchall()
        dict_rows = [dict(row) for row in rows]
        cls.data = {record["id"]: ConnectionModel(**record) for record in dict_rows}

class Promptlist(Data):
    @classmethod
    def refresh(cls):
        rows = LocalDatabase.connect().execute("SELECT * FROM prompts").fetchall()
        cls.data = {record["id"]: PromptModel(**record) for record in rows}

class VectorDBlist(Data):
    @classmethod
    def refresh(cls):
        rows = LocalDatabase.connect().execute("SELECT * FROM vectordb").fetchall()
        cls.data = {record["id"]: VectorDB(**record) for record in rows}

class LatticeTools(Data):
    @classmethod
    def refresh(cls):
        rows = LocalDatabase.connect().execute("SELECT * FROM latticetools").fetchall()
        cls.data = {record["id"]: ToolsModel(**record) for record in rows}

class LLMmodels():
    MODELS: Dict[str, Model] = {}

    def __init__(self) -> None:
        # For each connection refresh the list so that we use the latest connection info
        self.connections = LlmConnections.list()
        print(self.connections)
        for connection in self.connections:
            connec = LlmConnections.get(connection)
            if not connec:
                print(f"Connection {connection} not found.")
                continue
            Client=llmClient(**connec.model_dump(exclude_unset=True))
            models = Client.models()
            if models:
                for model in models:
                    self.MODELS.update({model.get('name'):Model(**model)})


    def listdown(self):
        if self.MODELS:
            print(f"Available models:{self.MODELS.keys()}")
            return list(self.MODELS.keys())
        else:
            print("No models available.")

    def list(self) -> Dict:
        """
        Returns a list of model names.
        """
        return self.MODELS

    def get(self, key):
        if key in self.MODELS:
            return self.MODELS[key]
        print(f"Model {key} not found.")
        return None
  
class Workflows:
        pass

class MCPClients:
        pass
