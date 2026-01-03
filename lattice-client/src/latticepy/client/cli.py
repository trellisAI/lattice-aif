import argparse
import os
import sys
import platform
import toml
import json
import requests

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

#check if config file exists inside the Lattice client folder
data={}

def config(action):
    global data
    if platform.system() == "Windows":
        home_dir = os.path.join(os.environ["USERPROFILE"])
    elif platform.system() == "Linux" or platform.system() == "Darwin":
        home_dir = os.path.expanduser("~")
    else:
        print(f"Unsupported operating system: {platform.system()}")
        sys.exit()
    lattice_folder = ".Lattice"
    lattice_path = os.path.join(home_dir, lattice_folder, 'client')

    if not os.path.exists(lattice_path):
        try:
            os.makedirs(lattice_path)
            print("Lattice Folder created successfully.")
        except OSError as e:
            print(f"Error: '{lattice_path}': {e}")
    
    if action == 'add' or action == 'edit':
        try:
            print("Generating config file inside Lattice client folder.")
            config = { 'url': input("Enter Lattice Server URL (default: http://localhost:44444/): ") or "http://localhost:44444/", 
                    'api_key': input("Enter API Key (default: None): ") or None,}
            with open(os.path.join(lattice_path, 'config.toml'), 'w') as f:
                toml.dump(config, f)
        except Exception as e:
            print(f"Error adding config file: {e}")
            exit(1)
    if action == 'clear':
        try:
            os.remove(os.path.join(lattice_path, 'config.toml'))
            print("Config file removed successfully.")
        except FileNotFoundError:
            print("Config file does not exist.")
        except Exception as e:
            print(f"Error removing config file: {e}")
            exit(1)
    if action == 'list':
        try:
            with open(os.path.join(lattice_path, 'config.toml'), 'r') as f:
                data=toml.load(f)
            print(data)
        except FileNotFoundError:
            print("Config file does not exist.")
            exit(1)
    try:
        with open(os.path.join(lattice_path, 'config.toml'), 'r') as f:
            data=toml.load(f)
    except FileNotFoundError:
        print("Config file does not exist.")



class Message(BaseModel):
    role: str
    content: str
    more: Optional[str] = None

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class ChatRequest(BaseModel):
    agent: Optional[str] = None
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    options: Optional[dict] = None
    format: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    headers: Dict[str, Any]
    choices: List[Choice]
    usage: Dict[str, int]

def engine(args):
    print("Starting Lattice Engine...")
    os.system("lattice-engine web")
    import multiprocessing as mp
    mp.set_start_method("spawn")
    from latticepy.engine.latticeai import main as engine_main
    p = mp.Process(target=engine_main, args=(args,))
    p.start()

   

def chat(llm, agent=None):
    print("Starting chat session. Type 'exit' to quit.")
    while True:
        user_input=input("You: ")
        if user_input.lower() == 'exit':
            print("Exiting chat session.")
            break
        #response=chatclient.send_message(user_input)
        request=ChatRequest(agent=agent, model=llm, messages=[Message(role="user", content=user_input)])
        #print(request.model_dump())
        response=requests.post(f"{data.get('url', 'http://localhost:44444')}/api/lattice/chat", json=request.model_dump())
        try:
            chat_response=ChatCompletionResponse.model_validate(response.json())
            for choice in chat_response.choices:
                print(f"Agent: {choice.message.content}")
        except Exception as e:
            print(f"Error in chat response: {e}")

class CliOptions:
    def __init__(self, ext) -> None:
        self.url=data.get('url', 'http://localhost:44444')
        self.api_key=data.get('api_key', None)
        self.headers={'Authorization': f'Bearer {self.api_key}'} if self.api_key else {}
        self.urle=f'{self.url}{ext}'

    def list(self, args=None):
        response=requests.get(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")
        

    def add(self, args=None):
        response=requests.post(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")
        

    def delete(self, args=None):
        response=requests.delete(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

    def clear(self, args=None):
        response=requests.delete(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

class AgentsCliOptions(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/agents'
        super().__init__(self.urle)

        
    def add(self, args=None):
        agent_id=input("Enter Agent ID: ")
        prompt=input("Enter Prompt name (optional): ") or None
        #tools_input=input("Enter tool names separated by commas (optional): ") or ""
        #tools=[tool.strip() for tool in tools_input.split(',')] if tools_input else []\
        toolfile=input("Enter tool function file: ")
        print("By default are tools are defined as 'rephrase', but that can be modified to 'pass' or 'flow' or 'rag'. more details available in wiki")
        try:
            with open(f"{os.getenv('LAT_CL_HOME_DIR')}/tools/{toolfile}", 'r') as f:
                tooljson=json.load(f)
                for tool in tooljson:
                    print(f"Tool added: {tool['function']['name']}")
                    tool_type=input("mention tool tyepe for the tool(rephrase): ") or 'rephrase'
                    if tool_type == 'flow':
                        toolflow=input("Enter tool followon name for flow action: ")
                        tool['details']={'action': 'flow', 'followon': toolflow}
                    elif tool_type == 'rag':
                        tool['details']={'action': 'RAG'}
                    elif tool_type == 'pass':
                        tool['details']={'action': 'pass'}
                    else:
                        tool['details']={'action': 'rephrase'}
        except Exception as e:
            print(f"Error loading tool function file: {e}")
            return
        payload={
            "id": agent_id,
            "prompt": prompt,
            "tools": tooljson
        }
        response=requests.post(self.urle, headers=self.headers, json=payload)
        if response.status_code == 200:
            print('saving the agent configuration: ')
            if not os.path.exists(f"{os.getenv('LAT_CL_HOME_DIR')}/agents/"):
                os.makedirs(f"{os.getenv('LAT_CL_HOME_DIR')}/agents/")
            with open(f"{os.getenv('LAT_CL_HOME_DIR')}/agents/{agent_id}_config.json", 'w') as f:
                json.dump(payload, f, indent=4)
        else:
            print(f"Error: {response.status_code} - {response.text}")

    def edit(self, args=None):
        agent_id=input("Enter Agent ID to edit: ")
        prompt=input("Enter new Prompt name (leave blank to keep current): ") or None
        toolfile=input("Enter new tool function file (leave blank to keep current): ") or None
        payload={}
        if prompt:
            payload['prompt']=prompt
        if toolfile:
            try:
                with open(f"{os.getenv('LAT_CL_HOME_DIR')}/tools/{toolfile}", 'r') as f:
                    tooljson=json.load(f)
                    for tool in tooljson:
                        print(f"Tool added: {tool['function']['name']}")
                        tool_type=input("mention tool tyepe for the tool(rephrase): ") or 'rephrase'
                        if tool_type == 'flow':
                            toolflow=input("Enter tool followon name for flow action: ")
                            tool['details']={'action': 'flow', 'followon': toolflow}
                        elif tool_type == 'rag':
                            tool['details']={'action': 'RAG'}
                        elif tool_type == 'pass':
                            tool['details']={'action': 'pass'}
                        else:
                            tool['details']={'action': 'rephrase'}
            except Exception as e:
                print(f"Error loading tool function file: {e}")
                return
            payload['tools']=tooljson
        response=requests.put(f"{self.urle}/{agent_id}", headers=self.headers, json=payload)
        if response.status_code == 200:
            print('updating the agent configuration: ')
            if not os.path.exists(f"{os.getenv('LAT_CL_HOME_DIR')}/agents/"):
                os.makedirs(f"{os.getenv('LAT_CL_HOME_DIR')}/agents/")
            with open(f"{os.getenv('LAT_CL_HOME_DIR')}/agents/{agent_id}_config.json", 'w') as f:
                json.dump(payload, f, indent=4)
        else:
            print(f"Error: {response.status_code} - {response.text}")

class ConnCliOptions(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/connections'
        super().__init__(self.urle)

class PromptsCliOptions(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/prompts'
        super().__init__(self.urle)

class RAGCliOptions(CliOptions):
    pass

class MCPCliOptions(CliOptions):
    pass

class LatticeToolServer(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/toolserver'
        super().__init__(self.urle)

    def add(self, args=None):
        name=input("Enter Tool Server name: ")
        url=input("Enter Tool Server URL: ")
        details=input("Enter additional details (optional): ") or {}
        payload={
            "id": name,
            "url": url,
            "details": details
        }
        response=requests.post(self.urle, json=payload)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

class ToolsData(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/tools'
        super().__init__(self.urle)

    def fetch(self, args):
        name=args.name[0] if args.name else None
        if not name:
            if args.all:
                response=requests.get(f"{self.urle}")
                if response.status_code == 200:
                    data=response.json()
                    print(*data['Lattice Tools'].keys(),sep='\n')
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                return
            elif args.alldetails:
                response=requests.get(f"{self.urle}")
                if response.status_code == 200:
                    data=response.json()
                    print(data)
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                return
            else:
                print("Tool server name is required for fetching tools.")
                return
        else:
            response=requests.get(f"{self.urle}/{name}")
            if response.status_code == 200:
                print(response.json())
            else:
                print(f"Error: {response.status_code} - {response.text}")


    def generate_tool_function_format(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the tool function format for a given tool.
        """
        # 1. Map Python types/objects to JSON Schema strings
        type_mapping = {
            int: "integer",
            str: "string",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"

        }

        properties = {}
        print(tool_data)
        args=tool_data['toolschema']['args']

        for arg in args:
            # Determine the string representation of the type
            json_type = arg['type']
            if not isinstance(json_type, str):
                json_type = type_mapping.get(arg.type, "string")
            
            if json_type == "array" and 'items' in arg:
                properties[arg['name']] = {
                    "type": json_type,
                    "description": arg['description'],
                    "items": {
                        "type": type_mapping.get(arg['items'], "string")
                    }
                }

            if json_type == "string" and 'enum' in arg:
                properties[arg['name']] = {
                    "type": json_type,
                    "description": arg['description'],
                    "enum": arg['enum']
                }

            properties[arg['name']] = {
                "type": json_type,
                "description": arg['description']
            }
            
            
        if 'required' not in tool_data['toolschema'].keys():
            required = [args['name'] for args in tool_data['toolschema']['args']]
        else:
            required = tool_data['toolschema']['args']['required']

        return {
            "type": "function",
            "function": {
                "name": tool_data['name'],
                "description": tool_data['description'],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    #generate tool function call format
    def gen(self, args=None):
        filename=input("Enter the tool file name to be saved (with .json extension): ")
        tools= input("Enter tool names separated by commas: ")
        tool_list=[tool.strip() for tool in tools.split(',')] if tools else []
        response=requests.get(f"{self.urle}")
        if response.status_code == 200:
            data=response.json()
            data=data['Lattice Tools']
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return
        tool_json=[]
        for tool in tool_list:
            if tool not in data.keys():
                print(f"Tool {tool} not found in the tool server.")
                continue
            tool_data=data[tool]['data']
            tool_data['name']=tool
            tool_json.append(self.generate_tool_function_format(tool_data))
        if not os.path.exists(f"{os.getenv('LAT_CL_HOME_DIR')}/tools/"):
            os.makedirs(f"{os.getenv('LAT_CL_HOME_DIR')}/tools/")
        with open(f"{os.getenv('LAT_CL_HOME_DIR')}/tools/{filename}", 'w') as f:
            json.dump(tool_json, f, indent=4)
        print(f"Tool function format saved to {filename}")

    def add(self, args=None):
        print("Tool addition not supported, they are auto loaded from the Tool server")

    def delete(self, args=None):
        print("Tool deletion not supported, they are auto loaded from the Tool server")

    def clear(self, args=None):
        print("Model clearing not supported, they are auto loaded from the connections")

class ModelOptions(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/models'
        super().__init__(self.urle)

    def add(self, args=None):
        print("Model addition not supported, they are auto loaded from the connections")

    def delete(self, args=None):
        print("Model deletion not supported, they are auto loaded from the connections")

    def clear(self, args=None):
        print("Model clearing not supported, they are auto loaded from the connections")

def main():
    print("Lattice Client CLI Tool")
    parser=argparse.ArgumentParser("lattice-client cli tool")
    subparsers=parser.add_subparsers(dest='isubcommand')
    parser_o= subparsers.add_parser('config')
    parser_o.add_argument("subcommand", choices=['edit', 'clear', 'add', 'list', 'load'])
    parser_h= subparsers.add_parser('chat')
    parser_h.add_argument("--agent", type=str, help="Agent name to use for chat", required=True)
    parser_h.add_argument("--llm", type=str, help="llm model to be used for chat", required=True)
    parser_a = subparsers.add_parser('agents')
    parser_a.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add', 'edit', 'download'])
    parser_c= subparsers.add_parser('connections')
    parser_c.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_p= subparsers.add_parser('prompt')
    parser_p.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_t= subparsers.add_parser('toolserver')
    parser_t.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add',])
    parser_l= subparsers.add_parser('tools')
    parser_l.add_argument("subcommand", choices=['list', 'fetch', 'gen'])
    parser_l.add_argument("--name", nargs=1)
    parser_l.add_argument("--all", action='store_true', help="Fetch all tools from all tool servers")
    parser_l.add_argument("--alldetails", action='store_true', help="Fetch all tools and details from all tool servers")
    parser_m= subparsers.add_parser('mcp')
    parser_m.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_d= subparsers.add_parser('models')
    parser_d.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_r= subparsers.add_parser('rag')
    parser_r.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_e= subparsers.add_parser('engine')
    parser_e.add_argument("run", choices=['web', 'daemon'])
    parser_e.add_argument("--port", type=int, help="Port number to run the client on", default=44444)
    parser_e.add_argument("--address", type=str, help="Address to run the client on", default="localhost")
    parser_e.add_argument("--socket", action='store_true', help="to enable socket communication")
    parser_e.add_argument("--config", type=str, help="Path to the configuration file", default=None)  
    args = parser.parse_args()
    if args.isubcommand == 'config':
        config(args.subcommand)

    elif args.isubcommand == 'engine':
        engine(args)

    elif args.isubcommand == 'chat':
        chat(args.llm, args.agent)

    else:
        call={
            'agents': AgentsCliOptions,
            'connections': ConnCliOptions,
            'prompts': PromptsCliOptions,
            'toolserver': LatticeToolServer,
            'tools': ToolsData,
            'models': ModelOptions,
            'rag': RAGCliOptions,
            'mcp': MCPCliOptions
        }

        met=call[args.isubcommand]()
        getattr(met, args.subcommand)(args)
        
if __name__ == "__main__":
    main()