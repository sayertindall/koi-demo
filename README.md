# KOI-net: Self-Forming Knowledge Mesh

![KOI-net Architecture](docs/images/koi-net-arch.png)

## Overview

KOI-net is a self-forming knowledge mesh that connects specialized nodes to create a distributed knowledge management system. The system collects, processes, indexes, and makes discoverable information from various sources through a coordinated network of dedicated nodes.

## System Architecture

KOI-net is organized around the following components:

### 1. Coordinator Node

The central hub for node discovery and connection management:

- Facilitates node discovery and edge formation
- Maintains the network topology
- Serves as the initial contact point for all nodes

### 2. Sensor Nodes

Specialized nodes that connect to external data sources:

- **GitHub Sensor** (`koi-net-github-sensor-node`):

  - Monitors GitHub repositories for new commits
  - Extracts relevant metadata and content
  - Publishes commit information to the network

- **HackMD Sensor** (`koi-net-hackmd-sensor-node`):
  - Tracks changes to HackMD notes
  - Captures note metadata and content
  - Makes notes discoverable in the knowledge mesh

### 3. Processor Nodes

Nodes that transform, index, and expose knowledge:

- **Processor A - GitHub Repository Indexer** (`koi-net-processor-a-node`):

  - Consumes GitHub commit events
  - Builds a searchable index of repository information
  - Provides a search API for querying commit data

- **Processor B - HackMD Note Indexer** (`koi-net-processor-b-node`):
  - Processes HackMD note events
  - Creates a multi-faceted index of notes
  - Exposes an API for searching and discovering notes

## KOI Protocol

The system leverages the KOI protocol, which provides:

- **Resource Identifiers (RIDs)**: Unique identifiers for all system resources
- **Manifest/Bundle Model**: Efficient metadata and content exchange
- **Edge System**: Self-forming connections between nodes
- **Event Propagation**: Real-time updates across the mesh

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Access to GitHub and/or HackMD instances

### Configuration

1. Copy sample configuration files:

   ```
   cp -r config/sample/* config/local/
   cp -r config/sample/* config/docker/
   ```

2. Modify configuration files in `config/local/` and `config/docker/` according to your environment.

3. Set up environment variables in `.env` file:
   ```
   GITHUB_TOKEN=your_github_token
   HACKMD_API_KEY=your_hackmd_api_key
   ```

### Running with Docker

Launch the entire system using Docker Compose:

```
docker-compose up
```

This will start all nodes in the correct order with appropriate networking.

### Running Locally

For development, you can run individual nodes locally:

1. Install dependencies for a specific node:

   ```
   cd nodes/koi-net-processor-a-node
   pip install -e .
   ```

2. Run the node:
   ```
   python -m processor_a_node
   ```

Repeat for other nodes as needed.

## Node Interconnections

The KOI-net system forms a directed knowledge graph:

```
                     ┌─────────────┐
                     │ Coordinator │
                     └──────┬──────┘
                 ┌───────── ┼ ────────┐
                 │          │         │
         ┌───────▼──┐  ┌────▼───┐ ┌───▼────┐
         │  GitHub  │  │ HackMD │ │   ...  │
         │  Sensor  │  │ Sensor │ │ Future │
         └───────┬──┘  └────┬───┘ └───────┘
                 │          │
         ┌───────▼──┐  ┌────▼───┐
         │Processor │  │Processor│
         │    A     │  │    B    │
         └──────────┘  └────────┘
```

Each node automatically discovers and connects to relevant nodes based on the RID types they produce and consume.

## Development

### Adding a New Node

1. Create a directory in `nodes/` for your new node
2. Implement the KOI protocol interfaces
3. Define the RID types the node provides and consumes
4. Add appropriate configuration in `config/`
5. Update the Docker Compose file to include the new node

### Extending Existing Nodes

Refer to each node's README for specific instructions on extending their capabilities:

- [Processor A - GitHub Repository Indexer](nodes/koi-net-processor-a-node/README.md)
- [Processor B - HackMD Note Indexer](nodes/koi-net-processor-b-node/README.md)

## Documentation

- [KOI Protocol Specification](docs/koi-protocol.md)
- [RID Library Documentation](docs/rid-lib.md)
- [Configuration Guide](docs/configuration.md)
- [Docker Deployment](docs/docker.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
