# Lattice Server

`lattice-server` is a lightweight utility for registering Python functions as tools, typically for use with Large Language Models (LLMs). It provides a decorator-based registry and Pydantic-powered schema validation to make it easy to expose local functions via a web API.

## Features

- **Tool Registration**: Use `@LatticeTool.tool` to register any function with a human-readable description and JSON schema.
- **Schema Validation**: Built-in support for Pydantic models to ensure tool metadata and responses are structured and valid.
- **Registry Access**: Easily retrieve all registered tools and their metadata for API discovery endpoints.
- **Standardized Responses**: Use `ToolResponse` and `ToolResHeaders` to ensure consistent API communication.

## Installation

```bash
pip install lattice-server
```

*(Note: If installing from source within the LatticePy workspace, use `pip install -e ./lattice-server`)*

## Basic Usage

### Registering a Tool

Use the `LatticeTool.tool` decorator to register a function. You must provide a `description` and a `schema`.

```python
from latticepy.server import LatticeTool

# Define a tool with a schema
@LatticeTool.tool(
    description="Calculate the square of a number.",
    schema={
        "args": [
            {"name": "n", "type": "int", "description": "The number to square."}
        ],
        "required": ["n"],
        "returns": [
            {"name": "result", "type": "int", "description": "The squared value."}
        ]
    }
)
def square(n: int) -> int:
    return n * n
```

### Retrieving Registered Tools

You can get a dictionary of all registered tools and their metadata using `LatticeTool.toollist()`.

```python
tools = LatticeTool.toollist()
print(tools["square"])
```



### Standardizing Responses

Use `ToolResponse` to wrap your tool's execution results.

```python
from latticepy.server import ToolResponse

try:
    result = square(n=5)
    response = ToolResponse(success=True, data=result)
except Exception as e:
    response = ToolResponse(success=False, error=str(e))

print(response.model_dump())
```

## API Endpoints

While `lattice-server` is framework-agnostic, it is designed to support the following standard endpoint patterns:

### `GET /api/get-tool-functions`
Returns a dictionary of all registered tools and their metadata. This is used by LLMs or clients for tool discovery.

### `POST /api/call-tool-function`
Executes a registered tool. Expects a JSON body with the following structure:
```json
{
  "function": "tool_name",
  "args": {
    "arg1": "value1"
  }
}
```

## Response Format

All tool executions should return a standardized `ToolResponse`.

### `ToolResponse`
| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | `bool` | Indicates if the tool executed successfully. |
| `data` | `Any` | The result of the tool execution (if successful). |
| `headers` | `ToolResHeaders` | Metadata about the response (optional). |
| `error` | `str` | Error message (if execution failed). |

### `ToolResHeaders`
| Field | Type | Description |
| :--- | :--- | :--- |
| `content_type` | `str` | The MIME type or format (e.g., "json", "csv", "image/png"). Defaults to "json". |
| `content_file_name`| `str` | Suggested filename if the data is a file. |
| `content_description`| `str` | A human-readable description of the return content. |

## Integration Example (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from latticepy.server import LatticeTool, ToolResponse, ToolResHeaders

app = FastAPI()

@app.get("/api/get-tool-functions")
def get_tools():
    return LatticeTool.toollist()

@app.post("/api/call-tool-function")
def call_tool(request: dict):
    func_name = request.get("function")
    args = request.get("args", {})
    
    tools = LatticeTool.toollist()
    if func_name not in tools:
        return ToolResponse(success=False, error=f"Tool {func_name} not found").model_dump()
        
    try:
        # Implementation of function lookup and execution
        # ...
        return ToolResponse(success=True, data=result).model_dump()
    except Exception as e:
        return ToolResponse(success=False, error=str(e)).model_dump()
```

## Development

To set up a development environment:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
