
# Get Started with Lattice AIF

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

3. Run the following command to start the sever(NOT SECURE: WIP)

   ```bash
   python -m LatticePy.latticeai interactive
   ```

more details `docs/details.md` 

#### Client Setup ( is directly available as application refer to packages.md)

if you wish to build locally refer client section `docs/details.md`


### 3. Configuration

Refer to the configuration documentation in the `docs/installation.md` file for advanced and environment-specific setup details.

---

You’re now ready to explore how to use Lattice AIF! Continue with the [Quick Start](quick-start.md) guide for your first project.
