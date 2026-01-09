import pytest

@pytest.fixture
def sample_tool_data():
    """
    Return a representative tool data structure used by generate_tool_function_format.
    """
    return {
        "name": "sampletool",
        "description": "A sample tool",
        "toolschema": {
            "args": [
                {"name": "text", "type": "string", "description": "input text", "required": True},
                {"name": "count", "type": "integer", "description": "number of items", "required": False},
                {"name": "modes", "type": "array", "description": "modes list", "items": "string", "required": False},
                {"name": "choice", "type": "string", "enum": ["a", "b"], "description": "an enum field", "required": False},
            ],
            "required": ["text"]
        }
    }

@pytest.fixture
def tmp_tools_dir(tmp_path, monkeypatch):
    """
    Ensure the default client directory is redirected to a tmp_path during tests.
    """
    test_dir = tmp_path / "client"
    test_dir.mkdir(parents=True)
    monkeypatch.setenv("LAT_CL_HOME_DIR", str(test_dir))
    return test_dir