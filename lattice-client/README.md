# Lattice Client

`lattice-client` is the primary command-line interface (CLI) for the Lattice AI framework. it allows you to manage agents, tools, connections, and perform interactive chat sessions with a Lattice server.

## Installation

```bash
pip install lattice-client
```

*(Note: If installing from source within the LatticePy workspace, use `pip install -e ./lattice-client`)*

## Getting Started

The first thing you should do is configure the client to point to your Lattice Server:

```bash
lattice config add
```

This will prompt you for the Server URL (default: `http://localhost:44444/`) and an optional API Key.

## CLI Commands

The `lattice` command (and its alias `latticepy-client`) provides several subcommands for managing different aspects of the framework.

### `config`
Manage local client configuration.
- `add`: Interactive prompt to add a new configuration.
- `edit`: Interactive prompt to update the existing configuration.
- `list` / `load`: Display the current configuration in JSON format.
- `clear`: Remove the local configuration file.

### `chat`
![alt text](../docs/images/image.png)
Start an interactive, persistent chat session with an LLM through a specific agent.
- **Required Arguments**:
  - `--agent <agent_name>`: The name of the registered agent to use.
  - `--llm <model_name>`: The model identifier (e.g., `gpt-4`, `claude-3-opus`).
- **Usage**:
  ```bash
  lattice chat --agent my-helper --llm gpt-4
  ```

### `agents`
Manage AI agents on the server and locally.
- `list`: List all agents registered on the server.
- `add`: Create a new agent interactively (prompts for ID, prompt, and tool configuration).
- `edit`: Update an existing agent's configuration.
- `delete`: Remove an agent from the server.
- `clear`: Clear the local agent registry.
- `download`: Download agent configurations from the server to the local workspace.

### `tools`
Interact with tools and tool servers.
- `list`: List all tools available across all connected tool servers.
- `fetch`: Get details for a specific tool.
  - Usage: `lattice tools fetch --name <tool_name>`
  - `--all`: Fetch all tools.
  - `--alldetails`: Fetch all tools including their full schemas.
- `gen`: Generate a local tool function configuration file from server-side definitions.
  - This is used to prepare tool configurations for an agent.
  - Usage: `lattice tools gen` (Interactive prompt for filename and tool names).

### `toolserver`
Manage remote tool servers that provide functions to agents.
- `add`: Register a new tool server by providing its name and URL.
- `list`: List all registered tool servers.
- `delete`: Unregister a tool server.
- `clear`: Remove all tool server registrations.

### `connections`
Manage external service connections (e.g., OpenAI, Anthropic, Vector DBs).
- `list`, `add`, `delete`, `clear`.

### `prompt`
Manage system prompts and templates.
- `list`, `add`, `delete`, `clear`.

### `models`
Manage model configurations.
- `list`, `add`, `delete`, `clear`.

### `rag`
Manage Retrieval-Augmented Generation (RAG) resources.
- `list`, `add`, `delete`, `clear`.

### `mcp`
Manage Model Context Protocol (MCP) resources.
- `list`, `add`, `delete`, `clear`.

### `engine`
Run the local Lattice engine directly from the CLI.
- `run <web|daemon>`: Starts the engine in either web mode (FastAPI) or as a background daemon.
- **Options**:
  - `--port`: Port for the engine (default: `44444`).
  - `--address`: Bind address (default: `localhost`).
  - `--socket`: Enable socket-based communication.

### `launch`
Launch the graphical user interface.
- `run ui`: Starts the Streamlit-based web interface for Lattice.

## Configuration & Data
By default, `lattice-client` stores its data (config, local agents, tool definitions) in:
- **Linux/macOS**: `~/.Lattice/client`
- **Windows**: `%USERPROFILE%\.Lattice\client`

You can override this location by setting the `LAT_CL_HOME_DIR` environment variable.

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License
MIT
