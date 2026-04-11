#!/usr/bin/env python3
"""
Lattice Client CLI - improved and hardened version.
"""
from __future__ import annotations

import typer
import getpass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm

console = Console()
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

from . import init_client_home

# Initialize module-level logger after reading environment defaults

CLIENT_DIR = init_client_home()

class MinimalFormatter(logging.Formatter):
    """A formatter that suppresses stack traces and stack info."""
    def formatException(self, ei):
        return ""
    def formatStack(self, stack_info):
        return ""

def setup_logging(level: Optional[str] = None, logfile: Optional[str] = None, debug: bool = False) -> logging.Logger:
    LOG_NAME = "latticeclient"
    env_level = os.getenv("LAT_CL_LOG_LEVEL", "INFO")
    env_file = Path(CLIENT_DIR) / "logs" / "lattice.log"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.touch(exist_ok=True)
    chosen_level = (level or env_level).upper()
    numeric_level = getattr(logging, chosen_level, logging.INFO)

    logger = logging.getLogger(LOG_NAME)
    
    # Standard format for files and debug mode
    verbose_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    # Minimal message-only format for standard CLI output
    minimal_formatter = MinimalFormatter("%(message)s")

    # If handlers already exist, we might want to update them (e.g., when main calls setup_logging with debug)
    if logger.handlers:
        logger.setLevel(numeric_level)
        for h in logger.handlers:
            h.setLevel(numeric_level)
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler):
                h.setFormatter(verbose_formatter if debug else minimal_formatter)
            else:
                h.setFormatter(verbose_formatter)
        return logger

    logger.setLevel(numeric_level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(verbose_formatter if debug else minimal_formatter)
    stream_handler.setLevel(numeric_level)
    logger.addHandler(stream_handler)

    path = logfile or env_file
    if path:
        try:
            fh = logging.handlers.RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
            fh.setFormatter(verbose_formatter)
            fh.setLevel(numeric_level)
            logger.addHandler(fh)
        except Exception:
            # If file handler can't be created, keep running with console logging
            # (using error instead of exception to avoid stack trace on console initialization)
            logger.error("Failed to create log file handler; continuing with console logging")

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
    config_path = CLIENT_DIR / "config.toml"
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
    ensure_client_dirs(CLIENT_DIR)
    config_path = CLIENT_DIR / "config.toml"
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
    try:
        return Confirm.ask(prompt, default=default)
    except (KeyboardInterrupt, EOFError):
        logger.info("Operation cancelled by user.")
        return False



def safe_input(prompt: str, default: Optional[str] = None, hide: bool = False) -> Optional[str]:
    """
    Read input from the user, returning default if blank. If hide=True uses getpass.
    """
    try:
        val = Prompt.ask(prompt, password=hide, default=default if default is not None else "")
    except (KeyboardInterrupt, EOFError):
        logger.info("Input interrupted by user.")
        return None
    val = val.strip()
    return val or None



def config(action: str) -> None:
    """
    Manage configuration actions: add, edit, clear, list, load
    - add / edit: prompt for URL and API key (api key entered hidden)
    - clear: remove config file
    - list / load: print currently loaded config
    """
    ensure_client_dirs(CLIENT_DIR)
    config_path = CLIENT_DIR / "config.toml"

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
            console.print_json(data=data)
        else:
            logger.info("Config file does not exist or is empty.")
        return

    logger.error("Unsupported config action: %s", action)


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


def make_session(api_key: Optional[str], timeout: int = 50, retries: int = 3) -> requests.Session:
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

"""
def engine(args) -> None:

    Start local engine. This function will attempt to import and spawn
    the engine in a new process. The previous behavior called an external
    command via os.system; choose one behavior and keep consistent.

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
"""

def chat(llm: str, agent: Optional[str] = None) -> None:
    console.print(Panel(f" Starting chat session with [cyan]{agent or 'default'}[/cyan] using [magenta]{llm}[/magenta].\n Welcome to LatticeAIF! \n Type 'exit' to quit.", title="Lattice Chat", border_style="green"))
    base_url = data.get("url", DEFAULT_BASE_URL)
    api_key = data.get("api_key", None)
    session = make_session(api_key)
    endpoint = urljoin(base_url.rstrip("/") + "/", "api/lattice/chat")
    while True:
        try:
            print("\n")
            user_input = Prompt.ask("[bold green]You[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting chat session.[/yellow]")
            break

        if user_input is None or user_input.strip().lower() in ("exit", "quit"):
            console.print("\n[yellow]Exiting chat session.[/yellow]")
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
            console.print("\n[bold blue]Agent:[/bold blue]")
            console.print(Markdown(choice.message.content))
            console.print("---")


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
            data = response.json()
            if isinstance(data, list):
                if not data:
                    console.print("[yellow]Empty[/yellow]")
                    return
                if isinstance(data[0], dict):
                    table = Table(show_header=True, header_style="bold magenta", border_style="cyan")
                    keys = data[0].keys()
                    for k in keys:
                        table.add_column(str(k))
                    for item in data:
                        table.add_row(*[str(item.get(k, "")) for k in keys])
                    console.print(table)
                else:
                    table = Table("Item", show_header=True, header_style="bold magenta", border_style="cyan")
                    for item in data:
                        table.add_row(str(item))
                    console.print(table)
            elif isinstance(data, dict):
                # Try to find a list value in the dict to render as table (e.g., {"connections": [...]})
                list_keys = [k for k, v in data.items() if isinstance(v, list)]
                if len(list_keys) == 1 and data[list_keys[0]]:
                    if isinstance(data[list_keys[0]][0], dict):
                        table = Table(title=list_keys[0].capitalize(), show_header=True, header_style="bold magenta", border_style="cyan")
                        keys = data[list_keys[0]][0].keys()
                        for k in keys:
                            table.add_column(str(k))
                        for item in data[list_keys[0]]:
                            table.add_row(*[str(item.get(k, "")) for k in keys])
                        console.print(table)
                    else:
                        table = Table(title=list_keys[0].capitalize(), show_header=True, header_style="bold magenta", border_style="cyan")
                        table.add_column("Item")
                        for item in data[list_keys[0]]:
                            table.add_row(str(item))
                        console.print(table)
                else:
                    console.print_json(data=data)
            else:
                console.print(data)
        except Exception as e:
            logger.exception("Error fetching list: %s", e)

    def add(self, args=None) -> None:
        try:
            response = self.session.post(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            console.print_json(data=response.json())
        except Exception as e:
            logger.exception("Error adding resource: %s", e)

    def delete(self, args=None) -> None:
        try:
            response = self.session.delete(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            console.print_json(data=response.json())
        except Exception as e:
            logger.exception("Error deleting resource: %s", e)

    def clear(self, args=None) -> None:
        # Default behavior: same as delete for the base endpoint
        try:
            response = self.session.delete(self.endpoint, timeout=self.session.request_timeout)
            response.raise_for_status()
            console.print_json(data=response.json())
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
        tools_path = CLIENT_DIR / "tools"
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
            agents_dir = CLIENT_DIR / "agents"
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
            tools_path = CLIENT_DIR / "tools"
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
            agents_dir = CLIENT_DIR / "agents"
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
            console.print_json(data=response.json())
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
                    table = Table("Tool Name", title="Lattice Tools", show_header=True, header_style="bold magenta", border_style="cyan")
                    for k in tools.keys():
                        table.add_row(str(k))
                    console.print(table)
                except Exception as e:
                    logger.exception("Error fetching all tools: %s", e)
                return
            elif getattr(args, "alldetails", False):
                try:
                    response = self.session.get(self.endpoint, timeout=self.session.request_timeout)
                    response.raise_for_status()
                    console.print_json(data=response.json())
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
                console.print_json(data=response.json())
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

        tools_dir = CLIENT_DIR / "tools"
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


app = typer.Typer(help="Lattice CLI - manage agents, tools, connections, and perform chat interactions with the Lattice server.", no_args_is_help=True)

config_app = typer.Typer(help="Manage local client configuration (url, api_key)", no_args_is_help=True)
app.add_typer(config_app, name="config")

agents_app = typer.Typer(help="Manage agents", no_args_is_help=True)
app.add_typer(agents_app, name="agents")

connections_app = typer.Typer(help="Manage connections", no_args_is_help=True)
app.add_typer(connections_app, name="connections")

prompts_app = typer.Typer(help="Manage prompts", no_args_is_help=True)
app.add_typer(prompts_app, name="prompt")

toolserver_app = typer.Typer(help="Manage tool servers", no_args_is_help=True)
app.add_typer(toolserver_app, name="toolserver")

tools_app = typer.Typer(help="Interact with tools and tool servers", no_args_is_help=True)
app.add_typer(tools_app, name="tools")

mcp_app = typer.Typer(help="Manage MCP resources", no_args_is_help=True)
app.add_typer(mcp_app, name="mcp")

models_app = typer.Typer(help="Manage models", no_args_is_help=True)
app.add_typer(models_app, name="models")

rag_app = typer.Typer(help="Manage RAG resources", no_args_is_help=True)
app.add_typer(rag_app, name="rag")

@app.callback()
def main_callback(debug: bool = typer.Option(False, "--debug", help="Enable debug logging")):
    if debug:
        setup_logging(level="DEBUG", debug=True)

@config_app.command("edit")
@config_app.command("add")
def config_add_edit():
    config("edit")

@config_app.command("clear")
def config_clear():
    config("clear")

@config_app.command("list")
@config_app.command("load")
def config_list_load():
    config("list")

@app.command("chat", help="Start an interactive chat session with an LLM")
def chat_cmd(
    agent: str = typer.Option(..., help="Agent name to use for chat"),
    llm: str = typer.Option(..., help="LLM model to be used for chat")
):
    chat(llm, agent)

"""
@app.command("engine", help="Run local engine")
def engine_cmd(
    run: str = typer.Argument(..., help="mode to run the client (web or daemon)"),
    port: int = typer.Option(44444, help="Port number to run the client on"),
    address: str = typer.Option("localhost", help="Address to run the client on"),
    socket: bool = typer.Option(False, help="to enable socket communication"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Path to the configuration file")
):
    class Args: pass
    args = Args()
    args.run = run
    args.port = port
    args.address = address
    args.socket = socket
    args.config = config_file
    engine(args)
"""

@app.command("launch", help="launch ui")
def launch_cmd(run: str = typer.Argument(..., help="'ui' to run web ui")):
    if run == "ui":
        launch_ui()
    else:
        logger.error("Command %s not supported for launch", run)

def bind_standard_commands(tgt_app: typer.Typer, cls) -> None:
    @tgt_app.command("list")
    def list_cmd():
        cls().list()
    @tgt_app.command("add")
    def add_cmd():
        cls().add()
    @tgt_app.command("delete")
    def delete_cmd():
        cls().delete()
    @tgt_app.command("clear")
    def clear_cmd():
        cls().clear()

bind_standard_commands(connections_app, ConnCliOptions)
bind_standard_commands(prompts_app, PromptsCliOptions)
bind_standard_commands(toolserver_app, LatticeToolServer)
bind_standard_commands(mcp_app, MCPCliOptions)
bind_standard_commands(models_app, ModelOptions)
bind_standard_commands(rag_app, RAGCliOptions)
bind_standard_commands(agents_app, AgentsCliOptions)

@agents_app.command("edit")
def agents_edit():
    AgentsCliOptions().edit()

@agents_app.command("download")
def agents_download():
    cmd = getattr(AgentsCliOptions(), "download", None)
    if cmd:
        cmd()
    else:
        logger.error("Command download not supported for agents")

@tools_app.command("list")
def tools_list():
    ToolsData().list()

@tools_app.command("fetch")
def tools_fetch(
    name: Optional[List[str]] = typer.Option(None, "--name", help="Tool server name or tool name depending on subcommand"),
    all: bool = typer.Option(False, "--all", help="Fetch all tools from all tool servers"),
    alldetails: bool = typer.Option(False, "--alldetails", help="Fetch all tools and details from all tool servers"),
):
    class Args: pass
    args = Args()
    args.name = name
    args.all = all
    args.alldetails = alldetails
    ToolsData().fetch(args)

@tools_app.command("gen")
def tools_gen():
    class Args: pass
    ToolsData().gen(Args())


def main() -> None:
    logger.info("Lattice Client CLI Tool")
    app()

if __name__ == "__main__":
    main()