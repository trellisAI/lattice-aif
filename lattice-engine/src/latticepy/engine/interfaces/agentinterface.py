from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json

from latticepy.engine.services.localdatabase import LocalDatabase
from latticepy.engine.interfaces.clientinterface import Promptlist
from latticepy.engine.services.toolengine import ToolData

LocalDatabase.create_tables(
    'latticeagents',
    {
        'id': 'TEXT PRIMARY KEY',
        'prompt': 'TEXT',
        'tools': 'TEXT',
        'details': 'TEXT'

    }
)


class LatticeAgent(BaseModel):
    id: str
    prompt: Optional[str]  = None
    tools: List[ToolData] = Field(default_factory=list)

    def create(self) -> None:
        """
        Create a new custom model with a unique ID.
        """
        if self.prompt and self.prompt not in Promptlist.list():
            raise ValueError(f"WARNING: prompt object  {self.prompt} not found in Promptlist")
        prompt_text=Promptlist.get(self.prompt).prompt if self.prompt else ''
        name = f"AGENT_{self.id}"
        try:
            print(name, prompt_text, self.tools)
            print("adding to agents to database")
            toollist=[]
            tooldetails={}
            for tool in self.tools:
                print(f'tool added: {tool.name}')
                tooldict=tool.genfunctioncall()
                tooldetails[tool.name]=tool.details.model_dump()
                toollist.append(tooldict)
            tool_text=json.dumps(toollist)
            tool_details=json.dumps(tooldetails)
            conn = LocalDatabase.connect()
            conn.execute(
                "INSERT INTO latticeagents (id, prompt, tools, details) VALUES (?, ?, ?)",
                (name, prompt_text, tool_text, tool_details)
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
        Clear all custom agents.
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
        
    @classmethod
    def update(cls):
        "update the tool or prompt data of existing agent"
        pass

