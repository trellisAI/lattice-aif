from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Literal, Tuple
import json
import jsonschema
import logging

logger = logging.getLogger(__name__)

from latticepy.engine.interfaces.serverinterface import servertooldata
from latticepy.engine.core.localdatabase import LocalDatabase


lb=LocalDatabase()

toolinfo = servertooldata()
tooldata, _ = toolinfo.listdetails()
class ToolLoad:
    """
    A class to load tools of latticepy agents
    It manages the configuration and execution of tools based on the model's capabilities.
    """

    def __init__(self, agentname):
        self.agentname = agentname
        logger.info(f"Loading tools for agent: {agentname}")
        with lb.get_connection() as conn:
            cursor=conn.execute("SELECT details FROM latticeagents WHERE id=?", (f'{agentname}',))
            row=cursor.fetchone()
        if not row:
            raise ValueError(f"Agent {agentname} not found in database.")
        logger.debug(f"Fetched tool details from database: {row['details']}")
        self.tooldetails=json.loads(row['details'])
        logger.debug(f"Tool details loaded: {self.tooldetails}")

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
        logger.info(f"Fetching recall option for tool: {tool} and {self.tooldetails}")
        details= self.tooldetails.get(tool, {})
        logger.debug(f"Tool details: {details}")
        return details.get('action', 'rephrase')
    
    def checktool(self, toolname) -> bool:
        """
        Check if the tool exists in the tooldata.
        """
        if toolname in tooldata.keys():
            return True
        return False
