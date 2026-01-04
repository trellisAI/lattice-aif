
from pydantic import BaseModel, Field,  ValidationError
from typing import Dict, Optional, Any, List, Tuple
import requests
import json

from latticepy.engine.services.localdatabase import LocalDatabase


LocalDatabase.create_tables(
    'toolservers',
    {
        'id': 'TEXT PRIMARY KEY',
        'url': 'TEXT',
        'details': 'TEXT'
    }   
)

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
    
def callserver(toolname, arguments):
    s=servertooldata()
    _ , function= toolname.split('.')
    url=s.tooldata[toolname]['url']
    tooljson = {'function': function, 'args': arguments}
    print(f'calling the function {tooljson}')
    data={}
    try:
        res=requests.post(f'{url}/call-tool-function', data=json.dumps(tooljson))
        res.raise_for_status()
        print(f"Response from server: {res.text}")
        data=ToolResponse.model_validate(res.json())
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while calling the function {tooljson}, error {e}")
    except Exception as e:
        print(f"error occured while calling the tool {e}")
    return data
    

class servertooldata:
    def __init__(self ):
        self.tooldata, self.server_tools =self.listdetails()

    def _get_tools(self, url) -> List:
        # get the tools from each server
        tool_models=[]
        try:
            res=requests.get(f'{url}/get-tool-functions')
            print(res.json())
            res.raise_for_status()
            tools=res.json()
            tool_models=[ToolDetails.model_validate(tool) for keys, tool in tools.items()]
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching the tools from {url}: {e}")
        except ValidationError:
            print("An error occured while vaildatind the tool from the server")
        except Exception as e:
            print(f"unknown error occured while fetching tools from server {e}")
        return tool_models

    @classmethod
    def add(cls, serverdata: ToolServer):
        # add in the database
        # get the tools shared by the server
        # Create an interface to get the tool data
        try:
            conn = LocalDatabase.connect()
            conn.execute(
                "INSERT INTO toolservers (id, url, details) VALUES (?, ?, ?)",
                (serverdata.id, serverdata.url, json.dumps(serverdata.details))
            )
            conn.connection.commit()
        except Exception as e:
            print(f"Error adding server: {e}")
            raise ValueError(f"Error adding server: {e}")

    def delete(self, server_id: str) -> bool:
        #delete the servers
        try:
            conn = LocalDatabase.connect()
            conn.execute("DELETE FROM toolservers WHERE id = ?", (server_id,))
            conn.connection.commit()
            print(f"Model {server_id} deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting server {server_id}: {e}")
            return False
        
    def list(self):
        rows = LocalDatabase.connect().execute("SELECT * FROM toolservers").fetchall()
        if rows:
            data={}
            for record in rows:
                data[record["id"]]= {**record}
            return data
        else:
            print("No servers available.")
            return {}
    
    def listdetails(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        #list the servers
        rows = LocalDatabase.connect().execute("SELECT * FROM toolservers").fetchall()
        #print(rows)
        if rows:
            data={}
            sdata={}
            for record in rows:
                server_tools=self._get_tools(record["url"])
                tooldata=[tool.model_dump() for tool in server_tools]
                print('fetched server tools:', server_tools)
                sdata.update({record["id"]:tooldata})
                data.update({f'{record["id"]}.{tool.name}':{'url':record["url"], 'data' : tool.model_dump()} for tool in server_tools})
            return data, sdata
        else:
            print("No servers available.")
            return {}, {}
