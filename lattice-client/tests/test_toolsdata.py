import pytest
from latticepy.client.cli import ToolsData

def test_generate_tool_function_basic(sample_tool_data):
    td = ToolsData()
    func = td.generate_tool_function_format(sample_tool_data)
    assert func["type"] == "function"
    fn = func["function"]
    assert fn["name"] == "sampletool"
    params = fn["parameters"]
    assert "text" in params["properties"]
    assert params["properties"]["text"]["type"] == "string"
    assert "count" in params["properties"]
    assert params["properties"]["count"]["type"] in ("integer", "number")

def test_generate_tool_function_array_and_enum(sample_tool_data):
    td = ToolsData()
    func = td.generate_tool_function_format(sample_tool_data)
    props = func["function"]["parameters"]["properties"]
    assert "modes" in props
    assert props["modes"]["type"] == "array"
    assert props["modes"]["items"]["type"] == "string"
    assert "choice" in props
    assert props["choice"]["enum"] == ["a", "b"]

def test_required_fields_priority(sample_tool_data):
    # if toolschema.required is present it should be used
    td = ToolsData()
    func = td.generate_tool_function_format(sample_tool_data)
    required = func["function"]["parameters"]["required"]
    assert "text" in required