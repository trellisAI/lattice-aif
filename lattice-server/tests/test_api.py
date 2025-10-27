import pytest
from typing import Dict, Any

# Assuming your tool logic (LatticeTool, lsendpoint, LATTICE_TOOL_REGISTRY) 
# is imported from the correct path.
# We'll use absolute imports assuming the test runner is configured correctly.
# If your tool logic is in `latticepy.server.tool`:
from latticepy.server.tool import (
    LatticeTool, 
    lsendpoint, 
    LATTICE_TOOL_REGISTRY, 
    ToolDetails
)

# --- Define a clean function for each test (important for isolation) ---

def define_example_tool(name: str):
    """Utility to define a test tool and register it."""
    # Define a unique schema for each tool name
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": f"The unique query for {name}."},
            "limit": {"type": "integer"}
        },
        "required": ["query"],
    }
    
    @LatticeTool(
        description=f"Tool for fetching data related to {name}.",
        schema=schema,
        return_desc=f"A list of results for {name}."
    )
    def test_func(query: str, limit: int = 10) -> list:
        """The actual function logic (rarely called in these tests)."""
        return [f"Result {i} for {query}" for i in range(limit)]

    return test_func

# --- Pytest Fixture to Ensure Registry Isolation ---

@pytest.fixture(autouse=True)
def clean_registry():
    """Fixture that clears the registry before and after each test."""
    # Before test: Ensure a clean slate
    LATTICE_TOOL_REGISTRY.clear()
    yield # Run the test
    # After test: Clean up again
    LATTICE_TOOL_REGISTRY.clear()


# ===============================================
# A. Tool Registration and Integrity Tests (Unit Tests)
# ===============================================

def test_decorator_registers_tool_correctly():
    """Verify that a decorated function is successfully added to the registry."""
    define_example_tool("test_tool_1")
    
    registry = lsendpoint()
    
    assert "test_func" in registry, "Tool function name must be a key in the registry."
    assert len(registry) == 1, "Only one tool should be registered."

def test_pydantic_schema_integrity():
    """Check that the registered data conforms to the ToolDetails model schema."""
    define_example_tool("test_tool_2")
    tool_data = lsendpoint()["test_func"]
    
    # 1. Check for required top-level keys
    required_keys = ["name", "description", "toolschema", "details"]
    assert all(k in tool_data for k in required_keys), "Tool data is missing required Pydantic fields."

    # 2. Re-validate against Pydantic model for extra assurance (optional but good)
    try:
        ToolDetails(**tool_data)
    except Exception as e:
        pytest.fail(f"Registered tool data failed Pydantic validation: {e}")

def test_metadata_content_accuracy():
    """Verify that the metadata passed to the decorator is accurately stored."""
    desc = "A crucial tool for testing."
    return_val = "Success status."
    
    @LatticeTool(description=desc, schema={}, return_desc=return_val)
    def check_metadata(x):
        return x
        
    tool_data = lsendpoint()["check_metadata"]
    
    assert tool_data["name"] == "check_metadata"
    assert tool_data["description"] == desc
    assert tool_data["details"]["returns"] == return_val

def test_multiple_tool_registration():
    """Verify that multiple decorated functions are all present."""
    # Register the first tool
    define_example_tool("first_tool")
    
    # Register a second tool
    @LatticeTool(description="Second", schema={}, return_desc="Second return")
    def second_func():
        pass
        
    registry = lsendpoint()
    
    assert len(registry) == 2, "The registry should contain exactly two tools."
    assert "test_func" in registry
    assert "second_func" in registry
    
def test_original_function_is_callable():
    """Ensure the original function remains callable and functional."""
    
    @LatticeTool(description="Math tool", schema={}, return_desc="Squared number")
    def square(n: int) -> int:
        return n * n
        
    # The decorator should not interfere with direct calls
    assert square(5) == 25, "The decorated function failed to execute its original logic."


# ===============================================
# B. Tool Execution Simulation Tests (API Interface)
# ===============================================

def test_get_tool_functions_endpoint_simulation():
    """Simulates the [GET] <server url>/api/get-tool-functions call."""
    
    # 1. Register a tool
    define_example_tool("api_test")
    
    # 2. Get the output of the exposed endpoint function
    api_output = lsendpoint()
    
    # 3. Validation
    assert isinstance(api_output, Dict), "Endpoint must return a dictionary."
    assert "test_func" in api_output, "Registered tool must be present in the API output."
    assert api_output["test_func"]["name"] == "test_func"


# Note: Your tool-server doesn't implement the [POST] /api/get-function-call 
# or the [GET] /api/get-tool-functions/<function>/schema endpoints directly 
# in the provided code, but we can test the data needed for them.

def test_extract_function_schema_for_llm_call():
    """Test extracting the raw schema, which would be used for LLM's function definition."""
    
    define_example_tool("schema_check")
    tool_data = lsendpoint()["test_func"]
    
    # This dictionary is what gets passed to the LLM
    llm_schema = tool_data["toolschema"]
    
    assert isinstance(llm_schema, Dict)
    assert llm_schema["type"] == "object"
    assert "properties" in llm_schema
    assert "query" in llm_schema["properties"]
    
    # This validates the data for the /api/get-tool-functions/<function>/schema endpoint