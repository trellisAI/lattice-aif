
## 🚀 Getting Started

Welcome to the Lattice AIF documentation! This guide will help you get started with the project, including an introduction and installation instructions.

## Introduction

Lattice AIF is an AI framework designed to help you build, deploy, and manage intelligent applications with ease. It provides a robust set of tools to create AI aagents with various capabilities and also seamless integration with your existing workflows.

The client-server architecture enables scalability, modularity, resource optimization, security and flexibility. This helps to build AI agents at scale with ease.

## Installation

To install Lattice AIF, follow these steps:

### 1. Clone the repository

```bash
git clone https://github.com/trellisAI/lattice-aif.git
cd lattice-aif
```

### 2. Install dependencies

Depending on your environment, follow the instructions below:

#### Server Setup

1. Navigate to the server directory:

   ```bash
   cd lattice-server
   ```

2. Install server dependencies (example using pip for Python):

   ```bash
   pip install -r requirements.txt
   ```

3. Run the following command to start the server (NOT SECURE: WIP)

   ```bash
   python -m LatticePy.latticeai interactive
   ```
   The idea is to have two modes: one interactive and the other a daemon mode, utilising a Unix daemon socket that runs continuously as a backend service. 

more details `docs/details.md` 

#### Client Setup

The client can be directly installed by adding the executable to the PATH.
To download the package, refer to `packages.md`

You can also build locally, refer to the client section `docs/details.md`

### 3. Configuration

Refer to the configuration documentation in the `docs/configuration.md` file for the inital configuration of the set up and get started

---

## 📖 Documentation

Our comprehensive documentation covers everything from installation and configuration to advanced agent development and deployment strategies.

**[Explore the Docs ↗](https://trellisai.github.io/lattice-aif/details.md)**

## 🌐 Community & Support

Join our community to connect with other developers, get support, and contribute to LatticeAI's growth:

* **GitHub Issues:** Report bugs or suggest features.
* **Discussions (Coming Soon):** Ask questions and engage with the community.
* **Discord/Slack (Future):** Real-time chat.

## 🤝 Contributing

We welcome contributions from the community! Whether it's code, documentation, or ideas, your input is valuable. Please see our `CONTRIBUTING.md` (coming soon) for guidelines.

## 📄 License

lattice-aif is released under the [MIT License](LICENSE).
