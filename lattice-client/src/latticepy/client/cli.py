import argparse
import os
import sys
import platform
import toml
import requests

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


class CliOptions:
    def __init__(self, ext) -> None:
        self.url=data.get('url', 'http://localhost:44444')
        self.api_key=data.get('api_key', None)
        self.headers={'Authorization': f'Bearer {self.api_key}'} if self.api_key else {}
        self.urle=f'{self.url}{ext}'

    def list(self):
        response=requests.get(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")
        

    def add(self):
        response=requests.post(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")
        

    def delete(self):
        response=requests.delete(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

    def clear(self):
        response=requests.delete(self.urle, headers=self.headers)
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")


class AgentsCliOptions(CliOptions):
    def __init__(self):
        self.urle='/api/lattice/agents'
        super().__init__(self.urle)


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
        self.urle='/api/lattice/toolservers'
        super().__init__(self.urle)

def main():
    parser=argparse.ArgumentParser("lattice-client cli tool")
    subparsers=parser.add_subparsers(dest='isubcommand')
    parser_o= subparsers.add_parser('config')
    parser_o.add_argument("subcommand", choices=['edit', 'clear', 'add', 'list', 'load'])
    parser_a = subparsers.add_parser('agent')
    parser_a.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_c= subparsers.add_parser('connections')
    parser_c.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_p= subparsers.add_parser('prompt')
    parser_p.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_t= subparsers.add_parser('toolserver')
    parser_t.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_m= subparsers.add_parser('mcp')
    parser_m.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    parser_r= subparsers.add_parser('rag')
    parser_r.add_argument("subcommand", choices=['list', 'clear', 'delete', 'add'])
    args = parser.parse_args()
    if args.isubcommand == 'config':
        config(args.subcommand)
    if args.isubcommand == 'connections':
        conn=ConnCliOptions()
        if args.subcommand == 'list':
            conn.list()
        if args.subcommand == 'add':
            conn.add()
        if args.subcommand == 'delete':
            conn.delete()
        if args.subcommand == 'clear':
            conn.clear()
    if args.isubcommand == 'agent':
        agent=AgentsCliOptions()
        if args.subcommand == 'list':
            agent.list()
        if args.subcommand == 'add':
            agent.add()
        if args.subcommand == 'delete':
            agent.delete()
        if args.subcommand == 'clear':
            agent.clear()
    if args.isubcommand == 'prompt':
        prompt=PromptsCliOptions()
        if args.subcommand == 'list':
            prompt.list()
        if args.subcommand == 'add':
            prompt.add()
        if args.subcommand == 'delete':
            prompt.delete()
        if args.subcommand == 'clear':
            prompt.clear()
    if args.isubcommand == 'toolserver':
        toolserver=LatticeToolServer()
        if args.subcommand == 'list':
            toolserver.list()
        if args.subcommand == 'add':
            toolserver.add()
        if args.subcommand == 'delete':
            toolserver.delete()
        if args.subcommand == 'clear':
            toolserver.clear()
    if args.isubcommand == 'mcp':
        mcp=VectorDBsCliOptions('/lattice/mcps')
        if args.subcommand == 'list':
            mcp.list()
        if args.subcommand == 'add':
            mcp.add()
        if args.subcommand == 'delete':
            mcp.delete()
        if args.subcommand == 'clear':
            mcp.clear()
    if args.isubcommand == 'rag':
        rag=RAGCliOptions('/lattice/rags')
        if args.subcommand == 'list':
            rag.list()
        if args.subcommand == 'add':
            rag.add()
        if args.subcommand == 'delete':
            rag.delete()
        if args.subcommand == 'clear':
            rag.clear()
    
if __name__ == "__main__":
    main()