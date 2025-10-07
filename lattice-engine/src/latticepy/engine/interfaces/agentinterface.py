from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json

from LatticePy.interfaces.localdatabase import LocalDatabase
from LatticePy.interfaces.clientinterface import Promptlist

from LatticePy.utils.toolcall import ToolConfig

LocalDatabase.create_tables(
    'latticeagents',
    {
        'id': 'TEXT PRIMARY KEY',
        'prompt': 'TEXT',
        'recalltools': 'TEXT'
    }   
)


class LatticeAgent(BaseModel):
    id: str
    prompt: Optional[str]  = None
    recalltools: ToolConfig

    def create(self) -> None:
        """
        Create a new custom model with a unique ID.
        """
        if self.prompt and self.prompt not in Promptlist.list():
            raise ValueError(f"WARNING: prompt not found in Promptlist, considering the {self.prompt}")
        prompt_text=Promptlist.get(self.prompt).prompt if self.prompt else ''
        name = f"AGENT_{self.id}"
        try:
            print(name, prompt_text, self.recalltools)
            print("adding to agents to database")
            tool_text=json.dumps(self.recalltools.model_dump())
            conn = LocalDatabase.connect()
            conn.execute(
                "INSERT INTO latticeagents (id, prompt, recalltools) VALUES (?, ?, ?)",
                (name, prompt_text, tool_text)
            )
            conn.connection.commit()
        except Exception as e:
            print(f"Error creating model: {e}")
            raise ValueError("Error creating model: {e}")
        
    @classmethod
    def list(cls) -> Dict[str, Any]:
        """
        List all custom models.
        """
        rows = LocalDatabase.connect().execute("SELECT * FROM latticeagents").fetchall()
        print(rows)
        if rows:
            return {record["id"]: {**record} for record in rows}
        else:
            print("No custom models available.")
            return {}
        
    @classmethod
    def listdown(cls) -> List[str]:
        """
        List all custom models.
        """
        rows = LocalDatabase.connect().execute("SELECT * FROM latticeagents").fetchall()
        print(rows)
        if rows:
            return [record["id"] for record in rows]
        else:
            print("No custom models available.")
            return []

    @classmethod
    def get(cls, model_id: str) -> Dict[str, Any]:
        """
        Get a specific custom model by ID.
        """
        row = LocalDatabase.connect().execute("SELECT * FROM latticeagents WHERE id = ?", (model_id,)).fetchone()
        if row:
            return {**row}
        else:
            print(f"Model {model_id} not found.")
            return {}
        
    @classmethod
    def delete(cls, model_id: str) -> bool:
        """
        Delete a custom model by ID.
        """
        try:
            conn = LocalDatabase.connect()
            conn.execute("DELETE FROM latticeagents WHERE id = ?", (model_id,))
            conn.connection.commit()
            print(f"Model {model_id} deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting model {model_id}: {e}")
            return False
        
    @classmethod
    def clear(cls) -> bool:
        """
        Clear all custom models.
        """
        try:
            conn = LocalDatabase.connect()
            conn.execute("DELETE FROM latticeagents")
            conn.connection.commit()
            print("All custom models cleared successfully.")
            return True
        except Exception as e:
            print(f"Error clearing custom models: {e}")
            return False