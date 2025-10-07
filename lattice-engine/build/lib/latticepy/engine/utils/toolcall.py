from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Literal, Tuple
import json

from LatticePy.interfaces.clientinterface import LatticeTools


alltools= LatticeTools.list()
available_tools=[]
funcs=[]
for tool in alltools:
    toolinfo=(LatticeTools.get(tool)).toollist
    toolfunctions=json.loads(toolinfo)
    for fun in toolfunctions:
        available_tools.append(fun.get('function').get('name'))
        funcs.append(fun.get('function'))

class RecallTools(BaseModel):
    name: str
    prompt: str
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="A dictionary for additional details about the tool.")
    action: Literal['rephrase', 'recall', 'filter', 'direct'] = Field('rephrase', description="Action to be taken with the tool. Options are 'rephrase', 'recall', 'filter', or 'direct'.")
    toolcall: Optional[str] = Field(None, description="Tool name to be called, if applicable. when the action is recall, this field is required.")

    @model_validator(mode='before')
    @classmethod
    def validate_action(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get('action') == 'recall' and not values.get('toolcall'):
            raise ValueError("When action is 'recall', toolcall must be provided.")
        if cls.action not in ['rephrase', 'recall', 'filter', 'direct']:
            raise ValueError("Action must be one of 'rephrase', 'recall', 'filter', or 'direct'.")
        return values

class ToolConfig(BaseModel):
    functions: List = ['all']
    details: Optional[List[RecallTools]] = []

class ToolCall:
    """
    A class to handle tool calls in LatticePy.
    It manages the configuration and execution of tools based on the model's capabilities.
    """

    def __init__(self, toolconfig):
        self.toolconfig = json.loads(toolconfig)
        self.active_tools = self._get_tools()

    def _get_tools(self) -> List[str]:
        """
        Returns a list of tools based on the provided configuration.
        """
        print('available tools:', available_tools)
        try:
            if self.toolconfig['functions'].pop() == 'all':
                return funcs
            else:
                return [func for func in funcs if func.get('name') in self.toolconfig['functions']]
        except Exception as e:
            # Handle exceptions and return an empty list or log the error
            print(f"Error fetching tools: {e}")
            return []   

    def getrecall(self, tool) -> Tuple[str, ...]:
        """
        Determines the recall option for a given tool.
        """
        if self.toolconfig.get('details'):
            for detail in self.toolconfig['details']:
                if detail['name'] and detail['name'] == tool:
                    return detail['action'], detail.get('prompt', None), detail.get('toolcall', None)
        return 'rephrase', None, None