"""
LatticeTool

Decorator around a function will add it to the set of tools that are exposed
by the server. The server should expose an endpoint such as:
    GET {url}/get_tool_functions
which returns the value of LatticeTool.toollist()

This version includes an automatic schema inference helper that builds a
ToolSchema from a Python function's signature and type annotations when
`schema=None` is passed to the decorator.
"""

from __future__ import annotations

import functools
import inspect
import logging
from threading import RLock
from typing import Dict, Any, Callable, Optional, Type, List, Union, get_origin, get_args, get_type_hints

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class PropertyDetails(BaseModel):
    name: str = Field(..., description="The name of the property.")
    type: Union[Type, str] = Field(..., description="The type of the property (e.g., 'str', 'int', list).")
    description: str = Field(..., description="A clear description of the property.")
    default: Optional[Any] = Field(None, description="The optional default value for the property.")

    @model_validator(mode="after")
    def _normalize_type(self) -> "PropertyDetails":
        # Convert a Python type to a canonical string representation for JSON-serializable metadata.
        if isinstance(self.type, type):
            self.type = self.type.__name__
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


def _type_to_str(tp: Any) -> str:
    """
    Convert a type annotation to a human-friendly, JSON-serializable string.
    Fallbacks to str(tp) for unknown/complex annotations.
    Examples:
        int -> "int"
        list[str] -> "list[str]"
        Optional[int] -> "Optional[int]"
        Union[int, str] -> "Union[int,str]"
    """
    # Handle direct types
    if tp is inspect._empty:
        return "Any"
    if isinstance(tp, type):
        return tp.__name__
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is None:
        # May be special typing object (e.g., typing.Any) or string forward ref
        try:
            return str(tp.__name__)  # works for many classes
        except Exception:
            return str(tp)
    # Handle Optional[T] (which is Union[T, NoneType])
    if origin is Union:
        # detect optional
        arg_names = [a for a in args]
        if len(arg_names) == 2 and type(None) in arg_names:
            other = arg_names[0] if arg_names[1] is type(None) else arg_names[1]
            return f"Optional[{_type_to_str(other)}]"
        return "Union[" + ",".join(_type_to_str(a) for a in args) + "]"
    # Generic containers
    origin_name = getattr(origin, "__name__", str(origin))
    if args:
        return f"{origin_name}[{', '.join(_type_to_str(a) for a in args)}]"
    return origin_name


def infer_schema_from_callable(func: Callable, include_return: bool = True) -> ToolSchema:
    """
    Infer a ToolSchema from a function's signature and type annotations.

    - Parameters without a default are considered required.
    - Parameter types are taken from annotations if present, otherwise 'Any'.
    - If include_return is True, return value is added as a single named property 'result'
      using the function's return annotation (or 'Any' if missing).

    Returns:
        ToolSchema instance.
    """
    sig = inspect.signature(func)
    hints = {}
    try:
        # get_type_hints resolves forward refs where possible
        hints = get_type_hints(func)
    except Exception:
        # Fallback: leave hints empty if resolution fails
        hints = {}

    args_props: List[PropertyDetails] = []
    required: List[str] = []
    for name, param in sig.parameters.items():
        # Skip VAR_POSITIONAL and VAR_KEYWORD for now (they can be supported as needed)
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            # Represent *args/**kwargs as a generic mapping/sequence
            ann = hints.get(name, param.annotation)
            tstr = _type_to_str(ann)
            desc = f"Parameter {name} (vararg/kwargs)."
            default_val = None if param.default is inspect._empty else param.default
            args_props.append(PropertyDetails(name=name, type=tstr, description=desc, default=default_val))
            # treat varargs/kwargs as optional if they have defaults
            if param.default is inspect._empty:
                required.append(name)
            continue

        ann = hints.get(name, param.annotation)
        tstr = _type_to_str(ann)
        desc = f"Parameter {name}."
        default_val = None if param.default is inspect._empty else param.default
        args_props.append(PropertyDetails(name=name, type=tstr, description=desc, default=default_val))
        if param.default is inspect._empty:
            required.append(name)

    returns_props: List[PropertyDetails] = []
    if include_return:
        ret_ann = hints.get("return", sig.return_annotation)
        ret_tstr = _type_to_str(ret_ann)
        returns_props.append(PropertyDetails(name="result", type=ret_tstr, description="Return value", default=None))
    else:
        returns_props = []

    # Build and validate ToolSchema via pydantic model
    schema = ToolSchema(args=args_props, required=required, returns=returns_props)
    return schema


class LatticeTool:
    """
    Registry and decorator helper for registering functions as 'tools'.
    Use:

        @LatticeTool.tool(description="...", schema=my_schema_or_None, details={})
        def my_tool(...): ...

    If `schema` is None, schema will be inferred from the function's signature.
    """
    registry: Dict[str, Dict[str, Any]] = {}
    _registry_lock = RLock()

    @staticmethod
    def tool(
        description: str,
        schema: Optional[Union[Dict[str, Any], ToolSchema]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """
        Decorator to register a function as an LLM tool.

        - description: human readable description of the tool.
        - schema: either a dict that validates against ToolSchema, a ToolSchema instance,
                  or None to enable automatic inference from the function signature.
        - details: optional extra metadata.
        """
        if details is None:
            details = {}

        def decorator_wrapper(func: Callable) -> Callable:
            nonlocal schema
            # If schema is None, infer from function signature
            if schema is None:
                try:
                    tschema = infer_schema_from_callable(func)
                except Exception as e:
                    logger.exception("Failed to infer schema for %s: %s", func.__name__, e)
                    raise
            else:
                # Normalize provided schema
                if isinstance(schema, ToolSchema):
                    tschema = schema
                elif isinstance(schema, dict):
                    tschema = ToolSchema.model_validate(schema)
                else:
                    raise TypeError("schema must be a dict, a ToolSchema instance, or None")

            logger.debug("Registering tool function: %s", func.__name__)
            tool_data = ToolDetails(
                name=func.__name__,
                description=description,
                toolschema=tschema,
                details=details
            )
            with LatticeTool._registry_lock:
                LatticeTool.registry[func.__name__] = tool_data.model_dump()
                logger.debug("Current tool registry keys: %s", list(LatticeTool.registry.keys()))

            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                return func(*args, **kwargs)

            return wrapper

        return decorator_wrapper

    @classmethod
    def toollist(cls) -> Dict[str, Dict[str, Any]]:
        """
        Return a serializable mapping of registered tools and their metadata.

        Intended to be returned by the server endpoint GET /get_tool_functions (or similar).
        """
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
# 1) Automatic schema inference:
# @LatticeTool.tool(description="Add two integers", schema=None)
# def add(a: int, b: int) -> int:
#     return a + b
#
# After registration, LatticeTool.toollist() will contain a ToolSchema inferred from
# the `add` function (args: a:int, b:int; required: ['a','b']; returns: result:int).
#
# 2) Provide explicit schema (when you need richer descriptions or different return names):
# @LatticeTool.tool(
#     description="Concatenate strings",
#     schema={
#         "args": [
#             {"name": "s1", "description": "first string", "type": "str"},
#             {"name": "s2", "description": "second string", "type": "str", "default": ""}
#         ],
#         "required": ["s1"],
#         "returns": [
#             {"name": "combined", "description": "concatenated result", "type": "str"}
#         ]
#     },
#     details={}
# )
# def concat(s1, s2=""):
#     return s1 + s2