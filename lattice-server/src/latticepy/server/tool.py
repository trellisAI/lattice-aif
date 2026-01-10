"""
LatticeTool

Decorator around a function will add it to the set of tools that are exposed
by the server. The server should expose an endpoint such as:
    GET {url}/get_tool_functions
which returns the value of LatticeTool.toollist()

Notes:
- Use LatticeTool.tool(...) as a decorator:
    @LatticeTool.tool(description="...", schema=my_schema, details={})
    def my_tool(...): ...
"""

from __future__ import annotations

import functools
import logging
from threading import RLock
from typing import Dict, Any, Callable, Optional, Type, List, Union

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class PropertyDetails(BaseModel):
    name: str = Field(..., description="The name of the property.")
    type: Union[Type, str] = Field(..., description="The type of the property (e.g., 'str', 'int', 'list').")
    description: str = Field(..., description="A clear description of the property.")
    default: Optional[Any] = Field(None, description="The optional default value for the property.")

    @model_validator(mode="after")
    def _normalize_type(self) -> "PropertyDetails":
        # Convert a Python type to a canonical string representation for JSON-serializable metadata.
        if isinstance(self.type, type):
            # Use the type name (e.g. 'str', 'int', 'list', 'dict') for portability.
            self.type = self.type.__name__
        # If it's already a string, keep it as-is.
        return self


class ToolSchema(BaseModel):
    args: List[PropertyDetails] = Field(..., description="A list defining the arguments (parameters) for the tool.")
    required: List[str] = Field(..., description="A list of required argument names.")
    returns: List[PropertyDetails] = Field(..., description="A list defining the return values for the tool.")

    @model_validator(mode="after")
    def validate_required_args(self) -> "ToolSchema":
        arg_names = {arg.name for arg in self.args}
        for req in self.required:
            if req not in arg_names:
                raise ValueError(f"The required argument '{req}' is not defined in the 'args' list.")
        return self


class ToolDetails(BaseModel):
    name: str = Field(..., description="The name of the function/tool.")
    description: str = Field(..., description="A clear, human-readable description for the LLM.")
    toolschema: ToolSchema = Field(..., description="The JSON schema defining the function's arguments and return type.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional metadata.")


class LatticeTool:
    """
    Registry and decorator helper for registering functions as 'tools'.
    Use:

        @LatticeTool.tool(description="...", schema=my_schema, details={})
        def my_tool(...): ...
    """
    # registry maps function name -> serializable dict (ToolDetails.model_dump())
    registry: Dict[str, Dict[str, Any]] = {}
    _registry_lock = RLock()

    @staticmethod
    def tool(description: str, schema: Union[Dict[str, Any], ToolSchema], details: Optional[Dict[str, Any]] = None) -> Callable:
        """
        Decorator to register a function as an LLM tool.

        - description: human readable description of the tool.
        - schema: either a dict that validates against ToolSchema or a ToolSchema instance.
        - details: optional extra metadata.
        """
        if details is None:
            details = {}

        # Normalize schema input to a ToolSchema instance
        if isinstance(schema, ToolSchema):
            tschema = schema
        elif isinstance(schema, dict):
            tschema = ToolSchema.model_validate(schema)
        else:
            raise TypeError("schema must be a dict or a ToolSchema instance")

        # The decorator that registers the function
        def decorator_wrapper(func: Callable) -> Callable:
            logger.debug("Registering tool function: %s", func.__name__)
            tool_data = ToolDetails(
                name=func.__name__,
                description=description,
                toolschema=tschema,
                details=details
            )
            with LatticeTool._registry_lock:
                # store a serializable representation
                LatticeTool.registry[func.__name__] = tool_data.model_dump()
                logger.debug("Current tool registry keys: %s", list(LatticeTool.registry.keys()))

            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # The wrapper is intentionally thin; it simply calls the original function.
                return func(*args, **kwargs)

            return wrapper

        return decorator_wrapper

    @classmethod
    def toollist(cls) -> Dict[str, Dict[str, Any]]:
        """
        Return a serializable mapping of registered tools and their metadata.

        Intended to be returned by the server endpoint GET /get_tool_functions (or similar).
        """
        # Shallow copy under lock to avoid concurrent mutation surprises.
        with cls._registry_lock:
            return dict(cls.registry)


class ToolResHeaders(BaseModel):
    content_type: str = Field("json", description="The content type of the response (file extension or mime shorthand).")
    content_file_name: Optional[str] = Field(None, description="If the content_type is a file, name of the file.")
    content_description: Optional[str] = Field(None, description="Description of the content.")


class ToolResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the tool execution was successful.")
    headers: Optional[ToolResHeaders] = Field(None, description="Headers providing metadata about the response.")
    data: Optional[Any] = Field(None, description="The data returned by the tool, if any.")
    error: Optional[str] = Field(None, description="Error message if the tool execution failed.")


# --- Example Usage ---
# Correct usage of the decorator:
# @LatticeTool.tool(
#     description="Get merged MR data for a particular project and tag",
#     schema={
#         "args": [
#             {"name": "project", "description": "name of the project", "type": "str"},
#             {"name": "tag", "description": "tag to filter merged MRs", "type": "str"},
#         ],
#         "required": ["project", "tag"],
#         "returns": [
#             {"name": "merged_mrs", "description": "List of merged MRs", "type": "list"}
#         ],
#     },
#     details={}
# )
