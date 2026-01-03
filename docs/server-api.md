```
class ToolResHeaders(BaseModel):
    content_type: str = Field('json', description="The content type of the response.")
    content_file_name: Optional[str] = Field('None', description='if the content_type is a file, name of the file')
    content_desciption: Optional[str]
    
class ToolResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the tool execution was successful.")
    headers: ToolResHeaders
    data: Optional[Dict[str, Any]] = Field(None, description="The data returned by the tool, if any.")
    error: Optional[str] = Field(None, description="Error message if the tool execution failed.")

```