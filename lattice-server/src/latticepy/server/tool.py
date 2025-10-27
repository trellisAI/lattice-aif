"""
LatticeTool Decorator around the function will add it to the list of the tools
that are exposed as tools available in server. user also needs to create an endpoint
f'{url}/get_tool_functions' which will expose the function lsenpoint

"""


from pydantic import BaseModel, Field
from typing import Dict, Any, Callable
import functools

# --- Pydantic Model (ToolDetails) ---

class ToolDetails(BaseModel):
    """Defines the standardized schema for exposing a tool's metadata."""
    name: str = Field(..., description="The name of the function/tool.")
    description: str = Field(..., description="A clear, human-readable description for the LLM.")
    toolschema: Dict[str, Any] = Field(..., description="The JSON schema defining the function's arguments.")
    details: Dict[str, Any] = Field(..., description="Additional metadata, like return description.")

# --- Global Tool Registry ---
# Using a dictionary to store the registered tool metadata
LATTICE_TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

# --- The Decorator ---

def LatticeTool(description: str, schema: Dict[str, Any], return_desc: str) -> Callable:
    """
    Decorator to register a function as an LLM tool.
    This uses the 'decorator with arguments' pattern.
    """
    def decorator_wrapper(func: Callable) -> Callable:
        # 1. Register the Tool's Metadata
        tool_data = ToolDetails(
            name=func.__name__,
            description=description,
            toolschema=schema,
            details={'returns': return_desc}
        )
        
        # Add to the global registry
        LATTICE_TOOL_REGISTRY[func.__name__] = tool_data.model_dump()
        print(LATTICE_TOOL_REGISTRY)

        # 2. Return the original function (or a wrapper if needed for logging/validation)
        # We use @functools.wraps to preserve function metadata (docstrings, name, etc.)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
        
    return decorator_wrapper

# --- The Tool-Server Endpoint Function ---

def lsendpoint() -> Dict[str, Dict[str, Any]]:
    """
    The endpoint function that exposes the registered tool details.
    Maps directly to the [GET] <server url>/api/get-tool-functions
    """
    return LATTICE_TOOL_REGISTRY

""" --- Example Usage ---

@LatticeTool(
    description="Calculates the square root of a positive number.",
    schema={
        "type": "object",
        "properties": {"number": {"type": "number", "description": "The positive number to square root."}},
        "required": ["number"],
    },
    return_desc="The square root of the input number."
)
def calculate_square_root(number: float) -> float:
    import math
    if number < 0:
        raise ValueError("Cannot calculate square root of a negative number.")
    return math.sqrt(number)

# Test the endpoint
# print(lsendpoint()) 
# print(calculate_square_root(9)) # Should still be callable as a regular function
"""