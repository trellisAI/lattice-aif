"""
LatticeTool Decorator around the function will add it to the list of the tools
that are exposed as tools available in server. user also needs to create an endpoint
f'{url}/get_tool_functions' which will expose the function lsenpoint

"""


from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any, Callable, Optional, Type, List, Union
import functools



class PropertyDetails(BaseModel):
    name: str = Field(..., description="The name of the property.")
    type: Union[Type, str] = Field(..., description="The type of the property (e.g., 'str', 'int', list).")
    description: str = Field(..., description="A clear description of the property.")
    default: Optional[Any] = Field(None, description="The optional default value for the property.")


class ToolSchema(BaseModel):
    args: List[PropertyDetails] = Field(..., description="A list defining the arguments (parameters) for the tool.")
    required: List[str] = Field(..., description="A list of required argument names.")
    returns: List[PropertyDetails] = Field(..., description="A list defining the return values for the tool.")

    @model_validator(mode='after')
    def validate_required_args(self) -> 'ToolSchema':
        arg_names = {arg.name for arg in self.args}
        for req in self.required:
            if req not in arg_names:
                raise ValueError(f"The required argument '{req}' is not defined in the 'args' list.")
        return self


class ToolDetails(BaseModel):
    name: str = Field(..., description="The name of the function/tool.")
    description: str = Field(..., description="A clear, human-readable description for the LLM.")
    toolschema: ToolSchema = Field(..., description="The JSON schema defining the function's arguments and return type.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional metadata.") # Changed default to None




class LatticeTool:
    registry: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def tool(description: str, schema: Union[Dict[str, Any], ToolSchema], details: Optional[Dict[str, Any]] = None) -> Callable:
        """
        Decorator to register a function as an LLM tool.
        Accepts either a plain `dict` schema or a `ToolSchema` instance.
        """
        if details is None:
            details = {}

        # Normalize schema input
        if isinstance(schema, ToolSchema):
            fschema = schema.model_dump()
        elif isinstance(schema, dict):
            fschema = ToolSchema.model_validate(schema)
        else:
            raise TypeError("schema must be a dict or a ToolSchema instance")

        def decorator_wrapper(func: Callable) -> Callable:
            print(func.__name__)
            tool_data = ToolDetails(
                name=func.__name__,
                description=description,
                toolschema=fschema,
                details=details
            )
            LatticeTool.registry[func.__name__] = tool_data.model_dump()
            print(LatticeTool.registry)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator_wrapper

    @classmethod
    def toollist(cls) -> Dict[str, Dict[str, Any]]:
        """
        The endpoint function that exposes the registered tool details.
        Maps directly to the [GET] <server url>/get-tool-functions
        """
        return cls.registry


class ToolResHeaders(BaseModel):
    content_type: str = Field('json', description="The content type of the response. possibly use the intended file extension")
    content_file_name: Optional[str] = Field('None', description='if the content_type is a file, name of the file')
    content_description: Optional[str] = Field('None', description='description of the content')

    
class ToolResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the tool execution was successful.")
    headers: Optional[ToolResHeaders] = Field(None, description="Headers providing metadata about the response.")
    data: Any = Field(None, description="The data returned by the tool, if any.")
    error: Union[str, None] = Field(None, description="Error message if the tool execution failed.")



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