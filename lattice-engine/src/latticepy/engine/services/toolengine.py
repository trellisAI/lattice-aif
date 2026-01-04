from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Literal, Tuple
import json
import jsonschema

from latticepy.engine.interfaces.serverinterface import servertooldata
from latticepy.engine.services.localdatabase import LocalDatabase


tooldata = servertooldata().tooldata


"""
class ToolDetails(BaseModel):
    action: Literal['rephrase', 'recall', 'filter', 'flow', 'RAG'] = Field('rephrase', description="Action to be taken with the tool. Options are 'rephrase', 'recall', 'filter', or 'direct'.")
    followon: Optional[str] = Field(None, description="Tool name to be called, if applicable. when the action is recall, this field is required.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the tool action.")

    @model_validator(mode='before')
    def validate_action(cls, values):
        # `values` is the raw input mapping for the model (before validation).
        # When action is 'recall', ensure 'followon' is provided.
        action = values.get('action') if isinstance(values, dict) else None
        followon = values.get('followon') if isinstance(values, dict) else None
        if action == 'recall' and not followon:
            raise ValueError("When action is 'recall', 'followon' must be provided.")
        return values


class ToolData(BaseModel):
    name: str
    prompt: str
    paramschema: Dict[str, Any]
    details: ToolDetails

    @model_validator(mode='before')
    def validateschema(cls, values):
        paramschema = values.get('paramschema') if isinstance(values, dict) else None
        if paramschema:
            try:
                jsonschema.Draft7Validator.check_schema(paramschema)
            except jsonschema.SchemaError as e:
                raise ValueError(f"Invalid schema: {e.message}")
        return values
        
    def genfunctioncall(self) -> Dict[str, Any]:


        return {
            "type": "function",
            "function": {
                    "name": self.name,
                    "description": self.prompt,
                    "parameters": self.paramschema["parameters"]
                }
        }

"""

class ToolLoad:
    """
    A class to load tools of latticepy agents
    It manages the configuration and execution of tools based on the model's capabilities.
    """

    def __init__(self, agentname):
        self.agentname = agentname
        print(f"Loading tools for agent: {agentname}")
        conn=LocalDatabase.connect()
        cursor=conn.execute("SELECT details FROM latticeagents WHERE id=?", (f'{agentname}',))
        row=cursor.fetchone()
        print(f"Fetched tool details from database: {row['details']}")
        if not row:
            raise ValueError(f"Agent {agentname} not found in database.")
        self.tooldetails=json.loads(row['details'])
        print(f"Tool details loaded: {self.tooldetails}")

    @staticmethod
    def get_server(toolname) -> str | None :
        """
        Returns the server on which the tool exists.
        """
        server = tooldata.get(toolname, None)
        return server

    def getrecall(self, tool) -> Dict[str, Any]:
        """
        Determines the recall option for a given tool.
        """
        print(f"Fetching recall option for tool: {tool} and {self.tooldetails}")
        details= self.tooldetails.get(tool, {})
        print(f"Tool details: {details}")
        return details.get('action', 'rephrase')
    
    def checktool(self, toolname) -> bool:
        """
        Check if the tool exists in the tooldata.
        """
        if toolname in tooldata.keys():
            return True
        return False