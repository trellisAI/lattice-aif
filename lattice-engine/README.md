# Lattice Engine

`lattice-engine` is the core orchestration layer of the Lattice AI framework. It manages the lifecycle of AI agents, coordinates tool execution, handles long-term memory via RAG, and provides a unified interface for multiple LLM providers.

## Developer Architecture

From a developer's perspective, the engine is structured as a collection of modular services coordinated by a central bootstrap process.

### 1. Bootstrapping & Configuration (`latticeai.py`)
The engine entry point initializes the local workspace (`~/.Lattice/server`) and loads configuration from `config.toml` using Pydantic for validation. It manages the lifecycle of sub-processes, primarily spawning the web server and database services.

### 2. Service Layer (`services/`)
The service layer implements the core logic of the framework:
- **`webserver.py`**: A FastAPI-based REST API that serves as the gateway for the `lattice-client`. It handles model registration, agent deployment, and chat session management.
- **`flowengine.py`**: Manages complex multi-step execution flows. It tracks state across agent interactions and ensures that tool outputs are correctly routed to the next step.
- **`toolengine.py`**: The execution runtime for Lattice Tools. It handles parameter mapping, execution of local tool functions, and communication with remote tool servers.
- **`localdatabase.py`**: An SQLite-based persistence layer that stores agent definitions, prompt templates, and connection metadata.

### 3. Interface Layer (`interfaces/`)
The engine uses an interface-driven design to ensure provider neutrality:
- **`LLMInterface`**: Abstract base class for LLM providers (OpenAI, Anthropic, local models via Ollama/vLLM).
- **`AgentInterface`**: Defines the lifecycle and execution contract for AI agents.
- **`ServerInterface`**: Defines how the engine communicates with external clients and tool registries.

### 4. Utilities & Extensions (`utils/`)
- **`RAG.py`**: Provides Retrieval-Augmented Generation capabilities. It integrates with vector databases to provide agents with contextual knowledge from local or remote documents.
- **`mcpclients.py`**: Implementation of the Model Context Protocol (MCP) client, allowing Lattice agents to seamlessly use any MCP-compliant tool server.

## Key Developer Workflows

### Registering a New LLM Provider
To add a new provider, implement the `LLMInterface` in `src/latticepy/engine/interfaces/llminterface.py` and register it in the connection management service.

### Customizing Agent Flows
Developers can modify `flowengine.py` to change how agents interact with one another or how they handle error recovery during complex task execution.

### Extending the API
All external interactions go through `webserver.py`. Adding new management capabilities involves creating new FastAPI routes and corresponding service methods.

## Data Persistence
The engine uses the following directory structure for persistent data:
- `~/.Lattice/server/config.toml`: Engine configuration.
- `~/.Lattice/server/localdb`: SQLite database file.
- `~/.Lattice/engine/logs/`: Rotating log files for debugging and monitoring.

## Installation for Development

```bash
# Clone the repository and install in editable mode
pip install -e ./lattice-engine

# The engine depends on several core AI libraries
pip install -r ./lattice-engine/requirements.txt
```

## Running the Engine

The engine can be started directly via the `lattice` CLI (from `lattice-client`) or as a standalone module:

```bash
python -m latticepy.engine.latticeai web --port 44444
```

## License
MIT
