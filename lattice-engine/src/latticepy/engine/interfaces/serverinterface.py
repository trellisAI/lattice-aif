
from pydantic import BaseModel, HttpUrl,  ValidationError
from typing import Dict, Optional, Any, List
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
    details: List[ToolDetails]
    
def callserver(toolname, arguments):
    s=servertooldata()
    _ , function= toolname.split('.')
    url=s.tools['toolname']
    tooljson = {'function': function, 'arguments': arguments}
    print(f'calling the function {tooljson}')
    try:
        res=requests.post(url, data=json.dumps(tooljson))
        res.raise_for_status()
        data=res.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while calling the function {tooljson}, error {e}")
    except Exception as e:
        print(f"error occured while calling the tool {e}")
    return data
    

class servertooldata:
    def __init__(self ):
        self.tools={}
        self.available_tools=[]
        self.tooldata=self._list()

    def _get_tools(self, url) -> List:
        # get the tools from each server
        tool_models=[]
        try:
            res=requests.get(f'{url}/get_tool_functions')
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
    
    def _list(self) -> Dict:
        #list the servers
        rows = LocalDatabase.connect().execute("SELECT * FROM toolservers").fetchall()
        print(rows)
        if rows:
            for record in rows:
                server_tools=self._get_tools(record["url"])
                print('fetched server tools:', server_tools)
                toolnames={f'{record["id"]}.{tool.name}': record["url"] for tool in server_tools}
                servertools=[tool.model_dump() for tool in server_tools]
                self.tools.update(toolnames)
                self.available_tools.extend(toolnames.keys())
                return {record["id"]: {**record,"tools":servertools} for record in rows}
        else:
            print("No servers available.")
            return {}