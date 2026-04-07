<p align="center">
  <img src="docs/logo.svg" alt="Lattice AI Logo" width="250"/>
</p>

Welcome to Lattice AIF, an AI framework for building intelligent applications.

## Lattice-AIF: New AI framework to create Agents

Lattice-AIF is an agentic framework and platform designed to build, deploy, and manage intelligent AI agents. LatticeAI Engine provides a unified abstraction layer over diverse Large Language Models (LLMs) and external tools, empowering you to create robust, actionable AI solutions with unprecedented flexibility. The client-server architecture is inspired from Docker client and Docker engine, helps to scale and mange the Agents.

## HLD architecture diagram
<img src="docs/latticeaif.drawio.svg" alt="Lattice AI Arch" width="100%"/>

## ✨ Why Lattice-AIF?

In a world of fragmented AI capabilities, LatticeAI brings order and efficiency:

* **LLM Agnostic:** Seamlessly integrate and switch between any LLM – from cloud-based powerhouses like Google Gemini and OpenAI to local, privacy-focused models like Ollama.
* **Robust Tool-Calling:** Extend LLM capabilities beyond text generation. Connect your agents to any API, database, or internal system to perform real-world actions.
* **Agent Orchestration:** Build complex, multi-step, multi-LLM agent workflows with ease, and manage their entire lifecycle.
* **Lattice Engine:** Inspired by Docker Engine, the arch is designed to benefit from a continuously running, daemonized "Lattice Engine" that provides production-grade reliability, scalability, and resource management for your agents.
* **Developer-Friendly:** Interact via a powerful Command Line Interface (CLI) for advanced users, and an intuitive platform for broader adoption (coming soon!).


## 📦 Package Structure

Lattice-AIF is organized into three core packages to ensure modularity and scalability:

- [**lattice-engine**](file:///home/pharsha/lattice-aif/lattice-engine/README.md): The core daemon and orchestration layer.
- [**lattice-client**](file:///home/pharsha/lattice-aif/lattice-client/README.md): The CLI and UI management layer for interacting with the engine.
- [**lattice-server**](file:///home/pharsha/lattice-aif/lattice-server/README.md): A lightweight utility for registering and exposing tools for agents.

## 🚀 Getting Started

To get started with Lattice AIF, you should first clone the repository and then proceed to the documentation for the specific component you wish to set up.

### 1. Clone the repository

```bash
git clone https://github.com/trellisAI/lattice-aif.git
cd lattice-aif
```

### 2. Component Setup

Depending on your role (developer vs. user), you may want to start with different components:

- **For Core Functionality**: Start with the [**Lattice Engine**](file:///home/pharsha/lattice-aif/lattice-engine/README.md). This is the heart of the framework and must be running for agents to function.
- **For Interaction & Management**: Refer to the [**Lattice Client**](file:///home/pharsha/lattice-aif/lattice-client/README.md) for details on using the CLI and UI to manage agents and sessions.
- **For Tool Development**: If you are building external tools for agents, see the [**Lattice Server**](file:///home/pharsha/lattice-aif/lattice-server/README.md) documentation on how to register and expose them.

### 3. Comprehensive Documentation

For more detailed guides on architecture, configuration, and advanced usage, please refer to the files in the `docs/` directory or visit our online documentation.

---

## 📖 Documentation

Our comprehensive documentation covers everything from installation and configuration to advanced agent development and deployment strategies.

**[Explore the Docs ↗](https://trellisai.github.io/lattice-aif/)**

## 🌐 Community & Support

Join our community to connect with other developers, get support, and contribute to LatticeAI's growth:

* **GitHub Issues:** Report bugs or suggest features.
* **Discussions (Coming Soon):** Ask questions and engage with the community.
* **Discord/Slack (Future):** Real-time chat.

## 🤝 Contributing

We welcome contributions from the community! Whether it's code, documentation, or ideas, your input is valuable. Please see our [CONTRIBUTING.md](file:///home/pharsha/lattice-aif/docs/CONTRIBUTING.md) for guidelines.

## 📄 License

Lattice-AIF is released under the [MIT License](LICENSE).