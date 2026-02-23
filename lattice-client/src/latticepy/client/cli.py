#!/usr/bin/env python3
"""
Lattice Client CLI - improved and hardened version.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging
import logging.handlers
import requests
import toml
from pydantic import BaseModel, Field

from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import init_client_home, default_client_dir

# Initialize module-level logger after reading environment defaults
LOG_NAME = "latticeclient"


def setup_logging(level: Optional[str] = None, logfile: Optional[str] = None) -> logging.Logger:
    """
    Configure logging for the CLI. Reads defaults from environment variables:
    - LAT_CL_LOG_LEVEL (e.g. DEBUG, INFO)
    - LAT_CL_LOG_FILE (path to log file)
    The `level` and `logfile` parameters override the environment settings.
    """
    env_level = os.getenv("LAT_CL_LOG_LEVEL", "INFO")
    env_file = os.getenv("LAT_CL_LOG_FILE")
    chosen_level = (level or env_level).upper()
    numeric_level = getattr(logging, chosen_level, logging.INFO)

    logger = logging.getLogger(LOG_NAME)
    if logger.handlers:
        # Avoid adding multiple handlers on repeated imports
        logger.setLevel(numeric_level)
        return logger

    logger.setLevel(numeric_level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(numeric_level)
    logger.addHandler(stream_handler)

    path = logfile or env_file
    if path:
        try:
            fh = logging.handlers.RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
            fh.setFormatter(formatter)
            fh.setLevel(numeric_level)
            logger.addHandler(fh)
        except Exception:
            # If file handler can't be created, keep running with console logging
            logger.exception("Failed to create log file handler; continuing with console logging")

    # Keep requests' debug logging quieter unless debug enabled for our logger
    if numeric_level > logging.DEBUG:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    else:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)

    return logger

logger = setup_logging()

# Global configuration store (populated by load_config)
data: Dict[str, Any] = {}

DEFAULT_BASE_URL = "http://localhost:44444/"


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
        logger.debug("Config file %s not found; using empty configuration", config_path)
        return
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = toml.load(f)
            logger.debug("Loaded configuration from %s", config_path)
    except Exception as e:
        logger.exception("Failed to load config file %s: %s", config_path, e)
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
        logger.info("Configuration saved to %s", config_path)
    except Exception as e:
        logger.exception("Failed to write config file %s: %s", config_path, e)
        raise
    # refresh global config
    load_config()


def confirm(prompt: str, default: bool = True) -> bool:
    """
    Ask user for a yes/no confirmation. Returns True for yes.
    """
    default_str = "Y/n" if default else "y/N"
    try:
        ans = input(f"{prompt} [{default_str}]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        logger.info("Operation cancelled by user.")
        return False
    if ans == "":
        return default
    return ans in ("y", "yes")


def safe_input(prompt: str, default: Optional[str] = None, hide: bool = False) -> Optional[str]:
    """
    Read input from the user, returning default if blank. If hide=True uses getpass.
    """
    try:
        if hide:
            val = getpass.getpass(prompt)
        else:
            val = input(prompt)
    except (KeyboardInterrupt, EOFError):
        logger.info("Input interrupted by user.")
        return None
    val = (val or "").strip()
    if not val and default is not None:
        return default
    return val or None


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
        logger.info("Generating/updating config file inside Lattice client folder.")
        url = safe_input(f"Enter Lattice Server URL (default: {DEFAULT_BASE_URL}): ", default=DEFAULT_BASE_URL) or DEFAULT_BASE_URL
        api_key = safe_input("Enter API Key (leave blank to omit): ", default=None, hide=True)
        save_config(url, api_key)
        logger.info("Config saved to %s", config_path)
        return

    if action == "clear":
        if not config_path.exists():
            logger.info("Config file does not exist.")
            load_config()
            return
        if not confirm(f"Are you sure you want to remove the config file at {config_path}?", default=False):
            logger.info("Config removal cancelled.")
            return
        try:
            config_path.unlink()
            logger.info("Config file removed successfully.")
        except Exception as e:
            logger.exception("Error removing config file: %s", e)
            raise
        # reload to clear data
        load_config()
        return

    if action in ("list", "load"):
        load_config()
        if data:
            # keep printed JSON on stdout for ease of piping
            print(json.dumps(data, indent=2))
        else:
            logger.info("Config file does not exist or is empty.")
        return

    logger.error("Unsupported config action: %s", action)


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
            logger.exception("Failed to validate chat response: %s", e)
            return None


def engine(args) -> None:
    """
    Start local engine. This function will attempt to import and spawn
    the engine in a new process. The previous behavior called an external
    command via os.system; choose one behavior and keep consistent.
    """
    import multiprocessing as mp

    logger.info("Starting Lattice Engine...")
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
        logger.exception("Failed to import local engine: %s. You may need to run the engine executable.", e)
        return

    p = mp.Process(target=engine_main, args=(args,))
    p.daemon = False
    p.start()
    logger.info("Engine process started (pid=%s).", p.pid)


def chat(llm: str, agent: Optional[str] = None) -> None:
    logger.info("Starting chat session. Type 'exit' to quit.")
    base_url = data.get("url", DEFAULT_BASE_URL)
    api_key = data.get("api_key", None)
    session = make_session(api_key)
    endpoint = urljoin(base_url.rstrip("/") + "/", "api/lattice/chat")
    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            logger.info("Exiting chat session.")
            break

        if user_input is None or user_input.strip().lower() in ("exit", "quit"):
            logger.info("Exiting chat session.")
            break

        request = ChatRequest(agent=agent, model=llm, messages=[Message(role="user", content=user_input)])
        try:
            # pydantic v2 uses model_dump(), v1 uses dict(); using model_dump if available
            payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            logger.debug("Posting chat payload to %s: %s", endpoint, payload)
            resp = session.post(endpoint, json=payload, timeout=session.request_timeout)
        except Exception as e:
            logger.exception("Network error posting chat request: %s", e)
            continue

        try:
            resp.raise_for_status()
        except Exception:
            logger.error("Server returned error: %s - %s", resp.status_code, resp.text)
            continue

        try:
            resp_json = resp.json()
        except Exception as e:
            logger.exception("Failed to parse JSON response: %s", e)
            logger.error("Unable to parse chat response.")
            continue

        chat_response = validate_chat_response(resp_json)
        if not chat_response:
            logger.error("Unable to validate chat response.")
            continue

        for choice in chat_response.choices:
            # Use print here to keep instant readability for chat interface (stdout)
            print(f"Agent: {choice.message.content}")


def launch_ui() -> None:
    """
    Launch the Streamlit UI for the Lattice client.
    """
    import streamlit.web.cli as stcli

    logger.info("Launching Lattice UI...")
    sys.argv = ["streamlit", "run", str(Path(__file__).parent / "ui.py")]
    sys.exit(stcli.main())

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
            logger.exception("Error fetching list: %s", e)

    def add(self, args=None) -> None:
        try:
            response = self.session.post(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            logger.exception("Error adding resource: %s", e)

    def delete(self, args=None) -> None:
        try:
            response = self.session.delete(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            logger.exception("Error deleting resource: %s", e)

    def clear(self, args=None) -> None:
        # Default behavior: same as delete for the base endpoint
        try:
            response = self.session.delete(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            logger.exception("Error clearing resource: %s", e)

class LatticeAgent(BaseModel):
    id: str
    prompt: Optional[str]  = None
    tools:  List[Dict[str, Any]] = Field(..., description="List of tool function definitions.")

class AgentsCliOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/agents")

    def add(self, args=None) -> None:
        agent_id = safe_input("Enter Agent ID: ", default=None)
        if not agent_id:
            logger.error("Agent ID is required.")
            return
        prompt = safe_input("Enter Prompt name (optional): ", default=None)
        toolfile = safe_input("Enter tool function file: ", default=None)
        if not toolfile:
            logger.error("Tool filename is required.")
            return
        logger.info("By default tools are defined as 'rephrase', but you can choose 'pass', 'flow', or 'rag'. See wiki for details.")
        tools_path = Path(default_client_dir()) / "tools"
        if not tools_path.exists():
            tools_path.mkdir(parents=True, exist_ok=True)
        toolfile_path = tools_path / toolfile
        try:
            with toolfile_path.open("r", encoding="utf-8") as f:
                tooljson = json.load(f)
        except Exception as e:
            logger.exception("Error loading tool function file: %s", e)
            return

        # allow interactive decoration of tool details
        for tool in tooljson:
            fname = tool.get("function", {}).get("name", "<unknown>")
            logger.info("Tool found: %s", fname)
            tool_type = safe_input("Mention tool type for the tool (rephrase/pass/flow/rag) [rephrase]: ", default="rephrase")
            if tool_type == "flow":
                toolflow = safe_input("Enter tool follow-on name for flow action: ", default="")
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
            logger.info("Saving the agent configuration locally.")
            agents_dir = Path(default_client_dir()) / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            with (agents_dir / f"{agent_id}_config.json").open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            logger.info("Agent %s created and saved locally.", agent_id)
        except Exception as e:
            logger.exception("Error creating agent: %s", e)

    def edit(self, args=None) -> None:
        agent_id = safe_input("Enter Agent ID to edit: ", default=None)
        if not agent_id:
            logger.error("Agent ID is required.")
            return
        prompt = safe_input("Enter new Prompt name (leave blank to keep current): ", default=None)
        toolfile = safe_input("Enter new tool function file (leave blank to keep current): ", default=None)
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
                logger.exception("Error loading tool function file: %s", e)
                return
            for tool in tooljson:
                fname = tool.get("function", {}).get("name", "<unknown>")
                logger.info("Tool found: %s", fname)
                tool_type = safe_input("Mention tool type for the tool (rephrase/pass/flow/rag) [rephrase]: ", default="rephrase")
                if tool_type == "flow":
                    toolflow = safe_input("Enter tool follow-on name for flow action: ", default="")
                    tool["details"] = {"action": "flow", "followon": toolflow}
                elif tool_type == "rag":
                    tool["details"] = {"action": "RAG"}
                elif tool_type == "pass":
                    tool["details"] = {"action": "pass"}
                else:
                    tool["details"] = {"action": "rephrase"}
            payload["tools"] = tooljson
        try:

            payLoad=LatticeAgent(id=agent_id, prompt=payload.get("prompt"), tools=payload.get("tools")).model_dump() if hasattr(LatticeAgent, "model_dump") else LatticeAgent(id=agent_id, prompt=payload.get("prompt"), tools=payload.get("tools")).dict()
            response = self.session.put(urljoin(self.endpoint + "/", agent_id), json=payLoad, timeout=self.session.request_timeout)
            response.raise_for_status()
            logger.info("Updating the agent configuration locally.")
            agents_dir = Path(default_client_dir()) / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)
            with (agents_dir / f"{agent_id}_config.json").open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            logger.info("Agent %s updated and saved locally.", agent_id)
        except Exception as e:
            logger.exception("Error updating agent: %s", e)


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
        name = safe_input("Enter Tool Server name: ", default=None)
        if not name:
            logger.error("Tool Server name is required.")
            return
        url = safe_input("Enter Tool Server URL: ", default=None)
        if not url:
            logger.error("Tool Server URL is required.")
            return
        details = safe_input("Enter additional details (optional): ", default="") or {}
        payload = {"id": name, "url": url, "details": details}
        try:
            response = self.session.post(self.endpoint, json=payload, timeout=self.session.request_timeout)
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            logger.exception("Error adding tool server: %s", e)


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
                    logger.exception("Error fetching all tools: %s", e)
                return
            elif getattr(args, "alldetails", False):
                try:
                    response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
                    response.raise_for_status()
                    print(response.json())
                except Exception as e:
                    logger.exception("Error fetching all tool details: %s", e)
                return
            else:
                logger.error("Tool server name is required for fetching tools.")
                return
        else:
            try:
                response = self.session.get(urljoin(self.endpoint + "/", name), timeout=self.session.request_timeout)
                response.raise_for_status()
                print(response.json())
            except Exception as e:
                logger.exception("Error fetching tool %s: %s", name, e)

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
                logger.debug("Skipping unnamed argument in toolschema: %s", arg)
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
        filename = safe_input("Enter the tool file name to be saved (with .json extension): ", default=None)
        if not filename:
            logger.error("Filename is required.")
            return
        tools = safe_input("Enter tool names separated by commas: ", default="")
        tool_list = [t.strip() for t in tools.split(",")] if tools else []
        try:
            response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            data_json = response.json()
            data_tools = data_json.get("Lattice Tools", {})
        except Exception as e:
            logger.exception("Error fetching tools from server: %s", e)
            return

        tool_json: List[Dict[str, Any]] = []
        for tool in tool_list:
            if tool not in data_tools:
                logger.warning("Tool %s not found in the tool server.", tool)
                continue
            tool_data = data_tools[tool].get("data", {})
            tool_data["name"] = tool
            try:
                tool_json.append(self.generate_tool_function_format(tool_data))
            except Exception as e:
                logger.exception("Failed to generate format for tool %s: %s", tool, e)

        tools_dir = Path(default_client_dir()) / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        target = tools_dir / filename
        try:
            with target.open("w", encoding="utf-8") as f:
                json.dump(tool_json, f, indent=4)
            logger.info("Tool function format saved to %s", target)
        except Exception as e:
            logger.exception("Failed to write tool file %s: %s", target, e)

    def add(self, args=None) -> None:
        logger.info("Tool addition not supported; tools are auto-loaded from the Tool server")

    def delete(self, args=None) -> None:
        logger.info("Tool deletion not supported; tools are auto-loaded from the Tool server")

    def clear(self, args=None) -> None:
        logger.info("Model clearing not supported; they are auto-loaded from the connections")


class ModelOptions(CliOptions):
    def __init__(self):
        super().__init__("/api/lattice/models")

    def add(self, args=None) -> None:
        logger.info("Model addition not supported; models are auto-loaded from the connections")

    def delete(self, args=None) -> None:
        logger.info("Model deletion not supported; models are auto-loaded from the connections")

    def clear(self, args=None) -> None:
        logger.info("Model clearing not supported; models are auto-loaded from the connections")


def main() -> None:
    logger.info("Lattice Client CLI Tool")
    parser = argparse.ArgumentParser(
        "lattice-client",
        description="Lattice CLI - manage agents, tools, connections, and perform chat interactions with the Lattice server.",
    )
    # Global options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="isubcommand")

    parser_o = subparsers.add_parser("config", help="Manage local client configuration (url, api_key)")
    parser_o.add_argument("subcommand", choices=["edit", "clear", "add", "list", "load"])

    parser_h = subparsers.add_parser("chat", help="Start an interactive chat session with an LLM")
    parser_h.add_argument("--agent", type=str, help="Agent name to use for chat", required=True)
    parser_h.add_argument("--llm", type=str, help="LLM model to be used for chat", required=True)

    parser_a = subparsers.add_parser("agents", help="Manage agents")
    parser_a.add_argument("subcommand", choices=["list", "clear", "delete", "add", "edit", "download"])

    parser_c = subparsers.add_parser("connections", help="Manage connections")
    parser_c.add_argument("subcommand", choices=["list", "clear", "delete", "add"])

    parser_p = subparsers.add_parser("prompt", help="Manage prompts")
    parser_p.add_argument("subcommand", choices=["list", "clear", "delete", "add"])

    parser_t = subparsers.add_parser("toolserver", help="Manage tool servers")
    parser_t.add_argument("subcommand", choices=["list", "clear", "delete", "add"])

    parser_l = subparsers.add_parser("tools", help="Interact with tools and tool servers")
    parser_l.add_argument("subcommand", choices=["list", "fetch", "gen"])
    parser_l.add_argument("--name", nargs=1, help="Tool server name or tool name depending on subcommand")
    parser_l.add_argument("--all", action="store_true", help="Fetch all tools from all tool servers")
    parser_l.add_argument("--alldetails", action="store_true", help="Fetch all tools and details from all tool servers")

    parser_m = subparsers.add_parser("mcp", help="Manage MCP resources")
    parser_m.add_argument("subcommand", choices=["list", "clear", "delete", "add"])

    parser_d = subparsers.add_parser("models", help="Manage models")
    parser_d.add_argument("subcommand", choices=["list", "clear", "delete", "add"])

    parser_r = subparsers.add_parser("rag", help="Manage RAG resources")
    parser_r.add_argument("subcommand", choices=["list", "clear", "delete", "add"])

    parser_e = subparsers.add_parser("engine", help="Run local engine")
    parser_e.add_argument("run", choices=["web", "daemon"])
    parser_e.add_argument("--port", type=int, help="Port number to run the client on", default=44444)
    parser_e.add_argument("--address", type=str, help="Address to run the client on", default="localhost")
    parser_e.add_argument("--socket", action="store_true", help="to enable socket communication")
    parser_e.add_argument("--config", type=str, help="Path to the configuration file", default=None)

    parser_u = subparsers.add_parser("launch", help="Run local engine")
    parser_u.add_argument("run", choices=['ui'])

    args = parser.parse_args()

    # Reconfigure logger if --debug passed
    if getattr(args, "debug", False):
        logger.setLevel(logging.DEBUG)
        for h in logger.handlers:
            h.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled via CLI flag")

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
    
    if args.isubcommand == "launch":
        if args.run == 'ui':
            launch_ui()

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
        logger.error("Unknown command: %s", args.isubcommand)
        return

    try:
        met = call[args.isubcommand]()
    except Exception as e:
        logger.exception("Failed to initialize CLI handler for %s: %s", args.isubcommand, e)
        return

    cmd = getattr(met, args.subcommand, None)
    if not cmd:
        logger.error("Command %s not supported for %s", args.subcommand, args.isubcommand)
        return

    try:
        cmd(args)
    except Exception as e:
        logger.exception("Unhandled exception while executing command: %s", e)


if __name__ == "__main__":
    init_client_home()
    main()