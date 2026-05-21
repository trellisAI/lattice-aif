
from pydantic import BaseModel, Field,  ValidationError
from typing import Dict, Optional, Any, List, Tuple
import requests
import json
import logging

logger = logging.getLogger(__name__)

from latticepy.engine.core.localdatabase import LocalDatabase
from latticepy.engine.core.pydanticmodels import ToolDetails, ToolServer, ToolResHeaders, ToolResponse

db = LocalDatabase() 

    
def callserver(toolname, arguments):
    s=servertooldata()
    _ , function= toolname.split('.')
    url=s.tooldata[toolname]['url']
    tooljson = {'function': function, 'args': arguments}
    logger.debug(f'calling the function {tooljson}')
    data={}
    try:
        res=requests.post(f'{url}/call-tool-function', data=json.dumps(tooljson))
        res.raise_for_status()
        logger.debug(f"Response from server: {res.text}")
        data=ToolResponse.model_validate(res.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while calling the function {tooljson}, error {e}")
    except Exception as e:
        logger.error(f"error occured while calling the tool {e}")
    return data
    

class servertooldata:
    def __init__(self ):
        self.tooldata={}
        self.server_tools ={}

    def _get_tools(self, url) -> List:
        # get the tools from each server
        tool_models=[]
        try:
            res=requests.get(f'{url}/get-tool-functions')
            logger.debug(res.json())
            res.raise_for_status()
            tools=res.json()
            tool_models=[ToolDetails.model_validate(tool) for keys, tool in tools.items()]
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while fetching the tools from {url}: {e}")
        except ValidationError:
            logger.error("An error occured while vaildatind the tool from the server")
        except Exception as e:
            logger.error(f"unknown error occured while fetching tools from server {e}")
        return tool_models

    @classmethod
    def add(cls, serverdata: ToolServer):
        # add in the database
        # get the tools shared by the server
        # Create an interface to get the tool data
        try:
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO toolservers (id, url, details) VALUES (?, ?, ?)",
                    (serverdata.id, serverdata.url, json.dumps(serverdata.details))
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error adding server: {e}")
            raise ValueError(f"Error adding server: {e}")

    def delete(self, server_id: str) -> bool:
        #delete the servers
        try:
            with db.get_connection() as conn:
                conn.execute("DELETE FROM toolservers WHERE id = ?", (server_id,))
                conn.commit()
            logger.info(f"Model {server_id} deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deleting server {server_id}: {e}")
            return False
        
    def list(self):
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM toolservers").fetchall()
            print('rows:', rows)
        if rows:
            data={}
            for record in rows:
                try:
                    data[record["id"]]= {'status': 'online' if requests.get(f'{record["url"]}/get-tool-functions').status_code == 200 else 'offline'}
                except Exception as e:
                    print(f"Error fetching status for {record['id']}: {e}")
                    data[record["id"]]= {'status': 'offline'}
            print('data',data)
            return data
        else:
            logger.info("No servers available.")
            return {}
    
    def listdetails(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        #list the servers
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM toolservers").fetchall()
        #print(rows)
        if rows:
            data={}
            sdata={}
            for record in rows:
                server_tools=self._get_tools(record["url"])
                tooldata=[tool.model_dump() for tool in server_tools]
                logger.debug(f'fetched server tools: {server_tools}')
                sdata.update({record["id"]:tooldata})
                data.update({f'{record["id"]}.{tool.name}':{'url':record["url"], 'data' : tool.model_dump()} for tool in server_tools})
            self.tooldata=data
            self.server_tools=sdata
            logger.debug(f"Loaded server data: {self.tooldata}")
            logger.debug(f"Loaded server tools: {self.server_tools}")
        else:
            logger.info("No servers available.")
        return self.tooldata, self.server_tools
