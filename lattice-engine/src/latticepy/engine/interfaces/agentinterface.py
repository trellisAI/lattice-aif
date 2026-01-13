from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json

from latticepy.engine.services.localdatabase import LocalDatabase
from latticepy.engine.interfaces.clientinterface import Promptlist
import logging

logger = logging.getLogger(__name__)
#from latticepy.engine.services.toolengine import ToolData

LocalDatabase.create_tables(
    'latticeagents',
    {
        'id': 'TEXT PRIMARY KEY',
        'prompt': 'TEXT',
        'tools': 'TEXT',
        'details': 'TEXT'

    }
)

#should we add memory field also to the agent?

class LatticeAgent(BaseModel):
    id: str
    prompt: Optional[str]  = None
    tools:  List[Dict[str, Any]] = Field(..., description="List of tool function definitions.")

    def create(self) -> None:
        """
        Create a new custom model with a unique ID.
        """
        #if self.prompt and self.prompt not in Promptlist.list():
        #    raise ValueError(f"WARNING: prompt object  {self.prompt} not found in Promptlist")
        prompt_text=Promptlist.get(self.prompt).prompt if self.prompt in Promptlist.list()  else self.prompt
        name = f"AGENT_{self.id}"
        try:
            logger.debug(f"{name}, {prompt_text}, {self.tools}")
            logger.info("adding to agents to database")
            tooldetails={}
            #tool_text=json.dumps(toollist)
            for tool in self.tools:
                tooldetails[tool['function']['name']]=tool.get('details', {})
                tool.pop('details', None)
            tool_text=json.dumps(self.tools)
            tooldetails=json.dumps(tooldetails)
            conn = LocalDatabase.connect()
            conn.execute(
                "INSERT INTO latticeagents (id, prompt, tools, details) VALUES (?, ?, ?, ?)",
                (name, prompt_text, tool_text, tooldetails)
            )
            conn.connection.commit()
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            raise ValueError("Error creating model: {e}")
        
    @classmethod
    def list(cls) -> Dict[str, Any]:
        """
        List all custom models.
        """
        rows = LocalDatabase.connect().execute("SELECT * FROM latticeagents").fetchall()
        logger.debug(rows)
        if rows:
            return {record["id"]: {**record} for record in rows}
        else:
            logger.info("No custom models available.")
            return {}
        
    @classmethod
    def listdown(cls) -> List[str]:
        """
        List all custom models.
        """
        rows = LocalDatabase.connect().execute("SELECT * FROM latticeagents").fetchall()
        logger.debug(rows)
        if rows:
            return [record["id"] for record in rows]
        else:
            logger.info("No custom models available.")
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
            logger.warning(f"Model {model_id} not found.")
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
            logger.info(f"Model {model_id} deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deleting model {model_id}: {e}")
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
            conn.connection.commit()
            logger.info("All custom models cleared successfully.")
            return True
        except Exception as e:
            logger.error(f"Error clearing custom models: {e}")
            return False
        
    @staticmethod
    def update(agent_id: str, data) -> None:
        "update the tool or prompt data of existing agent"
        try:
            conn = LocalDatabase.connect()
            if data['prompt'] is not None:
                conn.execute(
                    "UPDATE latticeagents SET prompt = ? WHERE id = ?",
                    (data['prompt'], agent_id)
                )
            if data['tools'] is not None:
                tool_text=json.dumps(data['tools'])
                conn.execute(
                    "UPDATE latticeagents SET tools = ? WHERE id = ?",
                    (tool_text, agent_id)
                )
            conn.connection.commit()
            logger.info(f"Agent {agent_id} updated successfully.")
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            raise ValueError("Error updating agent: {e}")
