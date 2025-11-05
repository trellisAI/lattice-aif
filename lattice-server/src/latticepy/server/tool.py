"""
LatticeTool Decorator around the function will add it to the list of the tools
that are exposed as tools available in server. user also needs to create an endpoint
f'{url}/get_tool_functions' which will expose the function lsenpoint

"""


from pydantic import BaseModel, Field
from typing import Dict, Any, Callable, Optional, Type, List, Union
import functools



class PropertyDetails(BaseModel):
    name: str = Field(..., description="The name of the property.")
    type: Union[Type, str] = Field(..., description="The type of the property (e.g., 'str', 'int', list).")
    description: str = Field(..., description="A clear description of the property.")
    default: Optional[Any] = Field(None, description="The optional default value for the property.")


class ToolSchema(BaseModel):
    args: List[PropertyDetails] = Field(..., description="A list defining the arguments (parameters) for the tool.")
    returns: List[PropertyDetails] = Field(..., description="A list defining the return values for the tool.")

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        [PropertyDetails.model_validate(arg) for arg in data.get("args", [])]
        [PropertyDetails.model_validate(ret) for ret in data.get("returns", [])]
        return data

class ToolDetails(BaseModel):
    name: str = Field(..., description="The name of the function/tool.")
    description: str = Field(..., description="A clear, human-readable description for the LLM.")
    toolschema: Dict[str, Any] = Field(..., description="The JSON schema defining the function's arguments and return type.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional metadata.") # Changed default to None


LATTICE_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def LatticeTool(description: str, schema: Dict, details: Dict[str, Any]={}) -> Callable:
    """
    Decorator to register a function as an LLM tool.
    This uses the 'decorator with arguments' pattern.
    """
    fschema= ToolSchema.validate(schema)
    def decorator_wrapper(func: Callable) -> Callable:
        print(func.__name__)
        tool_data = ToolDetails(
            name=func.__name__,
            description=description,
            toolschema=fschema,
            details=details
        )
        LATTICE_TOOL_REGISTRY[func.__name__] = tool_data.model_dump()
        print(LATTICE_TOOL_REGISTRY)

        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
        
    return decorator_wrapper

def lsendpoint() -> Dict[str, Dict[str, Any]]:
    """
    The endpoint function that exposes the registered tool details.
    Maps directly to the [GET] <server url>/api/get-tool-functions
    """
    return LATTICE_TOOL_REGISTRY

""" --- Example Usage ---
@LatticeTool( description = "get merged mr data for a particular project and tag", schema = {
             'args' : [
                 {
                     'name': 'project',
                     'description': 'name of the project',
                     'type': 'str',
                 },
                 # --- ADDED MISSING 'tag' ARGUMENT ---
                 {
                     'name': 'tag',
                     'description': 'The specific tag or label to filter the merged MRs.',
                     'type': 'str',
                 }
             ],
             'returns': [
                 {
                     'name' : 'sum',
                     'description': 'sum of numbers',
                     'type': 'list',
                 }
             ]
         },
         details={})
def get_sum_numbers2(number1, number2):
    sum=number1+number2
    return sum
"""