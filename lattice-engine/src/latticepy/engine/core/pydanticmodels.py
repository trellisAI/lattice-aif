from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional,  Literal, TypeAlias

class LatticeAgent(BaseModel):
    id: str
    prompt: Optional[str]  = None
    tools:  List[Dict[str, Any]] = Field(..., description="List of tool function definitions.")

class LocalDBModel(BaseModel):
    name: str
    db: Optional[str] = "sqlite3"
    url_path: str 
    password: Optional[str] = None

class ConfigModel(BaseModel):
    mode: str
    address: str
    port: int
    config_path: Optional[str] 
    SOCKET: Optional[bool] = False
    DATABASE: LocalDBModel
    TOOL_SERVER: Optional[str] = None


class ToolDetails(BaseModel):
    name: str
    description: str
    toolschema: Dict[str, Any]
    details: Dict[str, Any]

class ToolServer(BaseModel):
    id: str
    url: str
    details: Optional[Dict[str, Any]] = None

class ToolResHeaders(BaseModel):
    content_type: str = Field('json', description="The content type of the response.")
    content_file_name: Optional[str] = Field('None', description='if the content_type is a file, name of the file')
    content_desciption: Optional[str]
    
class ToolResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the tool execution was successful.")
    headers: Optional[ToolResHeaders] = Field(None, description="Headers providing metadata about the response.")
    data: Any = Field(None, description="The data returned by the tool, if any.")
    error: Optional[str] = Field(None, description="Error message if the tool execution failed.")

class PromptModel(BaseModel):
    id: str
    prompt: str

class VectorDB(BaseModel):
    id: str
    db: str = Field(default='postgres')  # default value for db
    url: str
    password: str
    tablename: str   # renamed from 'table'

llmSevers=Literal[
    'ollama',
    'gemini',
    'openai',
    'claude',
    'azure',
    'huggingface'
]

 
JsonString: TypeAlias = str

class ConnectionModel(BaseModel):
    id: str
    source: llmSevers
    url: str
    api_key: Optional[str]
    model: Optional[str] = None
    details: Optional[JsonString] = None


class Model(BaseModel):
    name: str
    model: str
    source: ConnectionModel
    details: Optional[Dict[str, Any]] = None