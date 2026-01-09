#!/usr/bin/env python3
"""
Lattice Client CLI - improved and hardened version.

This file contains fixes for:
- robust config loading/saving with secure permissions
- requests.Session usage with retries and timeouts
- defensive parsing of tool schemas
- fixed subclass __init__ for RAG/MCPCliOptions
- better handling of missing environment variables / defaults
- tolerant Pydantic v1 / v2 usage when validating chat responses
- safer file handling using pathlib

This is intended as an iterative improvement to make the module production-ready.
More improvements (tests, logging configuration, CLI UX) are recommended.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import toml
from pydantic import BaseModel

from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Global configuration store (populated by load_config)
data: Dict[str, Any] = {}

DEFAULT_BASE_URL = "http://localhost:44444/"


def default_client_dir() -> Path:
    # Use LAT_CL_HOME_DIR if set, otherwise default to ~/.Lattice/client
    env = os.getenv("LAT_CL_HOME_DIR")
    if env:
        return Path(env)
    return Path.home() / ".Lattice" / "client"


def ensure_client_dirs(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)


def load_config() -> None:
    """
    Load config from the user's client config file into the global `data` dict.
    If the file does not exist, `data` will stay empty.
    """
    global data
    client_dir = default_client_dir()
    config_path = client_dir / "config.toml"
    if not config_path.exists():
        data = {}
        return
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = toml.load(f)
    except Exception as e:
        print(f"Failed to load config file {config_path}: {e}", file=sys.stderr)
        data = {}


def save_config(url: Optional[str], api_key: Optional[str]) -> None:
    """
    Save configuration to the user's config file with secure permissions (0600).
    Passing api_key=None will omit the key from the file.
    """
    client_dir = default_client_dir()
    ensure_client_dirs(client_dir)
    config_path = client_dir / "config.toml"
    cfg: Dict[str, Any] = {}
    if url:
        cfg["url"] = url
    if api_key:
        cfg["api_key"] = api_key
    try:
        with config_path.open("w", encoding="utf-8") as f:
            toml.dump(cfg, f)
        # set file mode to 0o600
        config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        print(f"Failed to write config file {config_path}: {e}", file=sys.stderr)
        raise
    # refresh global config
    load_config()


def config(action: str) -> None:
    """
    Manage configuration actions: add, edit, clear, list, load
    - add / edit: prompt for URL and API key (api key entered hidden)
    - clear: remove config file
    - list / load: print currently loaded config
    """
    client_dir = default_client_dir()
    ensure_client_dirs(client_dir)
    config_path = client_dir / "config.toml"

    if action in ("add", "edit"):
        print("Generating/updating config file inside Lattice client folder.")
        url = input(f"Enter Lattice Server URL (default: {DEFAULT_BASE_URL}): ") or DEFAULT_BASE_URL
        api_key = getpass.getpass("Enter API Key (leave blank to omit): ") or None
        save_config(url, api_key)
        print(f"Config saved to {config_path}")
        return

    if action == "clear":
        try:
            config_path.unlink()
            print("Config file removed successfully.")
        except FileNotFoundError:
            print("Config file does not exist.")
        except Exception as e:
            print(f"Error removing config file: {e}", file=sys.stderr)
            raise
        # reload to clear data
        load_config()
        return

    if action in ("list", "load"):
        load_config()
        if data:
            print(json.dumps(data, indent=2))
        else:
            print("Config file does not exist or is empty.")
        return

    print(f"Unsupported config action: {action}", file=sys.stderr)


# Attempt to load config at import time so classes can pick up defaults
load_config()


# Pydantic models for response validation
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


def make_session(api_key: Optional[str], timeout: int = 10, retries: int = 3) -> requests.Session:
    s = requests.Session()
    # retry strategy for idempotent methods and server errors
    retry_strategy = Retry(
        total=retries,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]),
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    if api_key:
        s.headers.update({"Authorization": f"Bearer {api_key}"})
    # store default timeout as attribute for convenience (not used by requests automatically)
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


def validate_chat_response(resp_json: Any) -> Optional[ChatCompletionResponse]:
    """
    Validate JSON response using Pydantic (supports pydantic v2 or v1).
    Returns model or None on failure.
    """
    try:
        # pydantic v2
        return ChatCompletionResponse.model_validate(resp_json)
    except Exception:
        try:
            # pydantic v1
            return ChatCompletionResponse.parse_obj(resp_json)
        except Exception as e:
            print(f"Failed to validate chat response: {e}", file=sys.stderr)
            return None


def engine(args) -> None:
    """
    Start local engine. This function will attempt to import and spawn
    the engine in a new process. The previous behavior called an external
    command via os.system; choose one behavior and keep consistent.
    """
    import multiprocessing as mp

    print("Starting Lattice Engine...")
    # Set spawn method early if available
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        # start method already set; ignore
        pass

    # If the user wants the external command, we can run it. Otherwise spawn import.
    # For now try to import the engine entrypoint.
    try:
        from latticepy.engine.latticeai import main as engine_main  # type: ignore
    except Exception as e:
        print(f"Failed to import local engine: {e}. You may need to run the engine executable.", file=sys.stderr)
        return

    p = mp.Process(target=engine_main, args=(args,))
    p.daemon = False
    p.start()
    print(f"Engine process started (pid={p.pid}).")


def chat(llm: str, agent: Optional[str] = None) -> None:
    print("Starting chat session. Type 'exit' to quit.")
    base_url = data.get("url", DEFAULT_BASE_URL)
    api_key = data.get("api_key", None)
    session = make_session(api_key)
    endpoint = urljoin(base_url.rstrip("/") + "/", "api/lattice/chat")
    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat session.")
            break

        if user_input.strip().lower() in ("exit", "quit"):
            print("Exiting chat session.")
            break

        request = ChatRequest(agent=agent, model=llm, messages=[Message(role="user", content=user_input)])
        try:
            resp = session.post(endpoint, json=request.model_dump(), timeout=session.request_timeout)
        except Exception as e:
            print(f"Network error posting chat request: {e}", file=sys.stderr)
            continue

        try:
            resp.raise_for_status()
        except Exception:
            print(f"Server returned error: {resp.status_code} - {resp.text}", file=sys.stderr)
            continue

        resp_json = resp.json()
        chat_response = validate_chat_response(resp_json)
        if not chat_response:
            print("Unable to parse chat response.")
            continue

        for choice in chat_response.choices:
            print(f"Agent: {choice.message.content}")


class CliOptions:
    def __init__(self, ext: str) -> None:
        self.url = data.get("url", DEFAULT_BASE_URL)
        self.api_key = data.get("api_key", None)
        # normalize endpoint
        self.endpoint = urljoin(self.url.rstrip("/") + "/", ext.lstrip("/"))
        self.session = make_session(self.api_key)

    def list(self, args=None) -> None:
        try:
            response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            print(f"Error fetching list: {e}", file=sys.stderr)

    def add(self, args=None) -> None:
        try:
            response = self.session.post(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            print(f"Error adding resource: {e}", file=sys.stderr)

    def delete(self, args=None) -> None:
        try:
            response = self.session.delete(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            print(f"Error deleting resource: {e}", file=sys.stderr)

    def clear(self, args=None) -> None:
        # Default behavior: same as delete for the base endpoint
        try:
            response = self.session.delete(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            print(f"Error clearing resource: {e}", file=sys.stderr)


class AgentsCliOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/agents")

    def add(self, args=None) -> None:
        agent_id = input("Enter Agent ID: ").strip()
        if not agent_id:
            print("Agent ID is required.")
            return
        prompt = input("Enter Prompt name (optional): ") or None
        toolfile = input("Enter tool function file: ").strip()
        if not toolfile:
            print("Tool filename is required.")
            return
        print("By default tools are defined as 'rephrase', but you can choose 'pass', 'flow', or 'rag'. See wiki for details.")
        tools_path = Path(default_client_dir()) / "tools"
        if not tools_path.exists():
            tools_path.mkdir(parents=True, exist_ok=True)
        toolfile_path = tools_path / toolfile
        try:
            with toolfile_path.open("r", encoding="utf-8") as f:
                tooljson = json.load(f)
        except Exception as e:
            print(f"Error loading tool function file: {e}", file=sys.stderr)
            return

        # allow interactive decoration of tool details
        for tool in tooljson:
            fname = tool.get("function", {}).get("name", "<unknown>")
            print(f"Tool found: {fname}")
            tool_type = input("Mention tool type for the tool (rephrase/pass/flow/rag) [rephrase]: ") or "rephrase"
            if tool_type == "flow":
                toolflow = input("Enter tool follow-on name for flow action: ").strip()
                tool["details"] = {"action": "flow", "followon": toolflow}
            elif tool_type == "rag":
                tool["details"] = {"action": "RAG"}
            elif tool_type == "pass":
                tool["details"] = {"action": "pass"}
            else:
                tool["details"] = {"action": "rephrase"}

        payload = {
            "id": agent_id,
            "prompt": prompt,
            "tools": tooljson,
        }

        try:
            response = self.session.post(self.endpoint, json=payload, timeout=self.session.request_timeout)
            response.raise_for_status()
            print("Saving the agent configuration locally.")
            agents_dir = Path(default_client_dir()) / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            with (agents_dir / f"{agent_id}_config.json").open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            print(f"Error creating agent: {e}", file=sys.stderr)

    def edit(self, args=None) -> None:
        agent_id = input("Enter Agent ID to edit: ").strip()
        if not agent_id:
            print("Agent ID is required.")
            return
        prompt = input("Enter new Prompt name (leave blank to keep current): ") or None
        toolfile = input("Enter new tool function file (leave blank to keep current): ") or None
        payload: Dict[str, Any] = {}
        if prompt:
            payload["prompt"] = prompt
        if toolfile:
            tools_path = Path(default_client_dir()) / "tools"
            toolfile_path = tools_path / toolfile
            try:
                with toolfile_path.open("r", encoding="utf-8") as f:
                    tooljson = json.load(f)
            except Exception as e:
                print(f"Error loading tool function file: {e}", file=sys.stderr)
                return
            for tool in tooljson:
                fname = tool.get("function", {}).get("name", "<unknown>")
                print(f"Tool found: {fname}")
                tool_type = input("Mention tool type for the tool (rephrase/pass/flow/rag) [rephrase]: ") or "rephrase"
                if tool_type == "flow":
                    toolflow = input("Enter tool follow-on name for flow action: ").strip()
                    tool["details"] = {"action": "flow", "followon": toolflow}
                elif tool_type == "rag":
                    tool["details"] = {"action": "RAG"}
                elif tool_type == "pass":
                    tool["details"] = {"action": "pass"}
                else:
                    tool["details"] = {"action": "rephrase"}
            payload["tools"] = tooljson

        try:
            response = self.session.put(urljoin(self.endpoint + "/", agent_id), json=payload, timeout=self.session.request_timeout)
            response.raise_for_status()
            print("Updating the agent configuration locally.")
            agents_dir = Path(default_client_dir()) / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            with (agents_dir / f"{agent_id}_config.json").open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            print(f"Error updating agent: {e}", file=sys.stderr)


class ConnCliOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/connections")


class PromptsCliOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/prompts")


class RAGCliOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/rag")


class MCPCliOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/mcp")


class LatticeToolServer(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/toolserver")

    def add(self, args=None) -> None:
        name = input("Enter Tool Server name: ").strip()
        url = input("Enter Tool Server URL: ").strip()
        details = input("Enter additional details (optional): ") or {}
        payload = {"id": name, "url": url, "details": details}
        try:
            response = self.session.post(self.endpoint, json=payload, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            print(f"Error adding tool server: {e}", file=sys.stderr)


class ToolsData(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/tools")

    def fetch(self, args) -> None:
        name = args.name[0] if getattr(args, "name", None) else None
        if not name:
            if getattr(args, "all", False):
                try:
                    response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
                    response.raise_for_status()
                    data_json = response.json()
                    tools = data_json.get("Lattice Tools", {})
                    print(*tools.keys(), sep="\n")
                except Exception as e:
                    print(f"Error fetching all tools: {e}", file=sys.stderr)
                return
            elif getattr(args, "alldetails", False):
                try:
                    response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
                    response.raise_for_status()
                    print(response.json())
                except Exception as e:
                    print(f"Error fetching all tool details: {e}", file=sys.stderr)
                return
            else:
                print("Tool server name is required for fetching tools.")
                return
        else:
            try:
                response = self.session.get(urljoin(self.endpoint + "/", name), timeout=self.session.request_timeout)
                response.raise_for_status()
                print(response.json())
            except Exception as e:
                print(f"Error fetching tool {name}: {e}", file=sys.stderr)

    def generate_tool_function_format(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the tool function format for a given tool.

        Expected tool_data example:
        {
          "name": "toolname",
          "description": "desc",
          "toolschema": {
             "args": [
                {"name":"x","type":"string","description":"...","required":True, "enum":[...], "items":"string"}
             ],
             "required": ["x"]
          }
        }
        The implementation is defensive to handle missing keys and different type encodings.
        """
        type_mapping = {
            int: "integer",
            str: "string",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            "int": "integer",
            "integer": "integer",
            "str": "string",
            "string": "string",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "array": "array",
            "dict": "object",
            "object": "object",
        }

        toolschema = tool_data.get("toolschema", {}) or {}
        args = toolschema.get("args", []) or []

        properties: Dict[str, Any] = {}
        for arg in args:
            # arg is expected to be a dict
            name = arg.get("name")
            if not name:
                # skip unnamed args
                continue
            raw_type = arg.get("type", "string")
            # Normalize type
            if isinstance(raw_type, str):
                json_type = type_mapping.get(raw_type.lower(), raw_type)
            else:
                # If type provided as Python type object (unlikely), map
                json_type = type_mapping.get(raw_type, "string")

            prop: Dict[str, Any] = {"type": json_type}
            if "description" in arg:
                prop["description"] = arg.get("description")

            if json_type == "array":
                # items can be specified as arg['items'] as string/type
                items = arg.get("items")
                if items:
                    if isinstance(items, str):
                        item_type = type_mapping.get(items.lower(), "string")
                    else:
                        item_type = type_mapping.get(items, "string")
                    prop["items"] = {"type": item_type}
                else:
                    prop["items"] = {"type": "string"}

            if "enum" in arg:
                enum_val = arg.get("enum")
                if isinstance(enum_val, list):
                    prop["enum"] = enum_val

            properties[name] = prop

        # Determine required fields: prefer explicit toolschema.required, otherwise any arg with required=True
        if "required" in toolschema and isinstance(toolschema["required"], list):
            required = toolschema["required"]
        else:
            required = [a.get("name") for a in args if a.get("required")]

        return {
            "type": "function",
            "function": {
                "name": tool_data.get("name", "<unnamed>"),
                "description": tool_data.get("description", ""),
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
        }

    def gen(self, args=None) -> None:
        filename = input("Enter the tool file name to be saved (with .json extension): ").strip()
        if not filename:
            print("Filename is required.")
            return
        tools = input("Enter tool names separated by commas: ").strip()
        tool_list = [t.strip() for t in tools.split(",")] if tools else []
        try:
            response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            data_json = response.json()
            data_tools = data_json.get("Lattice Tools", {})
        except Exception as e:
            print(f"Error fetching tools from server: {e}", file=sys.stderr)
            return

        tool_json: List[Dict[str, Any]] = []
        for tool in tool_list:
            if tool not in data_tools:
                print(f"Tool {tool} not found in the tool server.")
                continue
            tool_data = data_tools[tool].get("data", {})
            tool_data["name"] = tool
            try:
                tool_json.append(self.generate_tool_function_format(tool_data))
            except Exception as e:
                print(f"Failed to generate format for tool {tool}: {e}", file=sys.stderr)

        tools_dir = Path(default_client_dir()) / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        target = tools_dir / filename
        try:
            with target.open("w", encoding="utf-8") as f:
                json.dump(tool_json, f, indent=4)
            print(f"Tool function format saved to {target}")
        except Exception as e:
            print(f"Failed to write tool file {target}: {e}", file=sys.stderr)

    def add(self, args=None) -> None:
        print("Tool addition not supported; tools are auto-loaded from the Tool server")

    def delete(self, args=None) -> None:
        print("Tool deletion not supported; tools are auto-loaded from the Tool server")

    def clear(self, args=None) -> None:
        print("Model clearing not supported; they are auto-loaded from the connections")


class ModelOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/models")

    def add(self, args=None) -> None:
        print("Model addition not supported; models are auto-loaded from the connections")

    def delete(self, args=None) -> None:
        print("Model deletion not supported; models are auto-loaded from the connections")

    def clear(self, args=None) -> None:
        print("Model clearing not supported; models are auto-loaded from the connections")


def main() -> None:
    print("Lattice Client CLI Tool")
    parser = argparse.ArgumentParser("lattice-client cli tool")
    subparsers = parser.add_subparsers(dest="isubcommand")
    parser_o = subparsers.add_parser("config")
    parser_o.add_argument("subcommand", choices=["edit", "clear", "add", "list", "load"])
    parser_h = subparsers.add_parser("chat")
    parser_h.add_argument("--agent", type=str, help="Agent name to use for chat", required=True)
    parser_h.add_argument("--llm", type=str, help="llm model to be used for chat", required=True)
    parser_a = subparsers.add_parser("agents")
    parser_a.add_argument("subcommand", choices=["list", "clear", "delete", "add", "edit", "download"])
    parser_c = subparsers.add_parser("connections")
    parser_c.add_argument("subcommand", choices=["list", "clear", "delete", "add"])
    parser_p = subparsers.add_parser("prompt")
    parser_p.add_argument("subcommand", choices=["list", "clear", "delete", "add"])
    parser_t = subparsers.add_parser("toolserver")
    parser_t.add_argument("subcommand", choices=["list", "clear", "delete", "add"])
    parser_l = subparsers.add_parser("tools")
    parser_l.add_argument("subcommand", choices=["list", "fetch", "gen"])
    parser_l.add_argument("--name", nargs=1)
    parser_l.add_argument("--all", action="store_true", help="Fetch all tools from all tool servers")
    parser_l.add_argument("--alldetails", action="store_true", help="Fetch all tools and details from all tool servers")
    parser_m = subparsers.add_parser("mcp")
    parser_m.add_argument("subcommand", choices=["list", "clear", "delete", "add"])
    parser_d = subparsers.add_parser("models")
    parser_d.add_argument("subcommand", choices=["list", "clear", "delete", "add"])
    parser_r = subparsers.add_parser("rag")
    parser_r.add_argument("subcommand", choices=["list", "clear", "delete", "add"])
    parser_e = subparsers.add_parser("engine")
    parser_e.add_argument("run", choices=["web", "daemon"])
    parser_e.add_argument("--port", type=int, help="Port number to run the client on", default=44444)
    parser_e.add_argument("--address", type=str, help="Address to run the client on", default="localhost")
    parser_e.add_argument("--socket", action="store_true", help="to enable socket communication")
    parser_e.add_argument("--config", type=str, help="Path to the configuration file", default=None)
    args = parser.parse_args()

    if not args.isubcommand:
        parser.print_help()
        return

    if args.isubcommand == "config":
        config(args.subcommand)
        return

    if args.isubcommand == "engine":
        engine(args)
        return

    if args.isubcommand == "chat":
        chat(args.llm, args.agent)
        return

    call = {
        "agents": AgentsCliOptions,
        "connections": ConnCliOptions,
        "prompts": PromptsCliOptions,
        "toolserver": LatticeToolServer,
        "tools": ToolsData,
        "models": ModelOptions,
        "rag": RAGCliOptions,
        "mcp": MCPCliOptions,
    }

    if args.isubcommand not in call:
        print(f"Unknown command: {args.isubcommand}", file=sys.stderr)
        return

    try:
        met = call[args.isubcommand]()
    except Exception as e:
        print(f"Failed to initialize CLI handler for {args.isubcommand}: {e}", file=sys.stderr)
        return

    cmd = getattr(met, args.subcommand, None)
    if not cmd:
        print(f"Command {args.subcommand} not supported for {args.isubcommand}", file=sys.stderr)
        return

    cmd(args)


if __name__ == "__main__":
    main()
