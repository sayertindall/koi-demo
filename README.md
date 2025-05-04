# KOI-net: Self-Forming Knowledge Mesh

![KOI-net Architecture](docs/images/koi-net-arch.png)

## Overview

KOI-net is a self-forming knowledge mesh that connects specialized nodes to create a distributed knowledge management system. The system collects, processes, indexes, and makes discoverable information from various sources through a coordinated network of dedicated nodes.

## System Architecture

KOI-net is organized around the following components:

### 1. Coordinator Node (`nodes/koi-net-coordinator-node`)

The central hub for node discovery and connection management:

- Facilitates node discovery and edge formation.
- Maintains the network topology.
- Serves as the initial contact point for all nodes.

### 2. Sensor Nodes

Specialized nodes that connect to external data sources:

- **GitHub Sensor** (`nodes/koi-net-github-sensor-node`):

  - Monitors GitHub repositories for new commits.
  - Extracts relevant metadata and content.
  - Publishes commit information (`GithubCommit` RIDs) to the network.

- **HackMD Sensor** (`nodes/koi-net-hackmd-sensor-node`):
  - Tracks changes to specified HackMD notes or teams.
  - Captures note metadata and content.
  - Publishes note information (`HackMDNote` RIDs) to the network.

### 3. Processor Nodes

Nodes that transform, index, and expose knowledge:

- **Processor A - GitHub Repository Indexer** (`nodes/koi-net-processor-a-node`):

  - Consumes `GithubCommit` events from the GitHub Sensor.
  - Builds a searchable index of repository commit information.
  - Provides a search API (`/search`) for querying commit data by SHA or keyword.

- **Processor B - HackMD Note Indexer** (`nodes/koi-net-processor-b-node`):
  - Consumes `HackMDNote` events from the HackMD Sensor.
  - Creates a searchable index based on note titles, tags, and IDs.
  - Exposes a search API (`/search`) for discovering notes by tag, title word, or note ID.

## KOI Protocol

The system leverages the KOI protocol, which provides:

- **Resource Identifiers (RIDs)**: Unique identifiers for all system resources (e.g., `GithubCommit`, `HackMDNote`). Uses `rid-lib`.
- **Manifest/Bundle Model**: Efficient metadata and content exchange.
- **Edge System**: Self-forming connections between nodes managed via the Coordinator.
- **Event Propagation**: Real-time updates across the mesh.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- `uv` (Python package manager, install via `pip install uv`)
- Access tokens/secrets for GitHub and HackMD.

### Configuration

1.  **Set up Environment Secrets:**

    - Copy the example environment file: `cp config/docker/global.env.example config/docker/global.env`
    - Edit `config/docker/global.env` and add your actual secrets:
      - `GITHUB_TOKEN`: Your GitHub Personal Access Token.
      - `HACKMD_TOKEN`: Your HackMD API Token.
      - `GITHUB_WEBHOOK_SECRET`: A secret string for verifying GitHub webhooks (if using webhook mode).

2.  **Review Node Configurations:**
    - Examine the YAML files in `config/docker/` (e.g., `github-sensor.yaml`, `hackmd-sensor.yaml`, `processor-a.yaml`, `processor-b.yaml`).
    - Adjust settings like monitored GitHub repos (`repos` list in `github-sensor.yaml`) or target HackMD notes/team (`target_note_ids` / `team_path` in `hackmd-sensor.yaml`) as needed.
    - **Note:** For local development, use the configurations in `config/local/` and adjust paths/URLs accordingly.

### Installation (Local Development)

1.  **Create Virtual Environment:**

    ```bash
    uv venv
    source .venv/bin/activate
    ```

2.  **Install All Packages:**
    - Use the Makefile for convenience:
      ```bash
      make install
      ```
    - _Alternatively, install manually:_ Install the root package and then each node package individually using `uv pip install -e .` in the respective directories (root, `nodes/*`, `rid_types`).

### Running with Docker (Recommended)

Launch the entire system using Docker Compose:

```bash
docker compose up --build -d
```

This command will:

- Build images for all nodes.
- Start containers in the correct dependency order.
- Run services in the background (`-d`).

Use `docker compose logs -f` to view aggregated logs or `docker compose logs -f <service_name>` (e.g., `processor-a`) for specific logs.

Stop the system with `docker compose down`.

### Running Locally (Development)

After running `make install`:

1.  Open separate terminal windows for each node you want to run.
2.  Activate the virtual environment in each terminal: `source .venv/bin/activate`
3.  Set the config mode: `export KOI_CONFIG_MODE=local`
4.  Run each node using the Makefile targets or directly:

    ```bash
    # Example: Run coordinator
    make coordinator
    # Or: python -m nodes.koi-net-coordinator-node.coordinator_node

    # Example: Run processor A
    make processor-a # (Add this target to Makefile if needed)
    # Or: python -m nodes.koi-net-processor-a-node.processor_a_node
    ```

## Node Interconnections

The KOI-net system forms a directed knowledge graph:

```
                     ┌─────────────┐
                     │ Coordinator │
                     └──────┬──────┘
                 ┌───────── ┼ ────────┐
                 │          │         │
         ┌───────▼──┐  ┌────▼───┐
         │  GitHub  │  │ HackMD │
         │  Sensor  │  │ Sensor │
         └───────┬──┘  └────┬───┘
                 │          │
         ┌───────▼──┐  ┌────▼───┐
         │Processor │  │Processor│
         │    A     │  │    B    │
         └──────────┘  └────────┘
```

- **Coordinator** connects to all nodes.
- **Sensors** connect to the Coordinator.
- **Processors** connect to the Coordinator and their respective **Sensors**.

Each node automatically discovers and connects to relevant peers based on the RID types they produce and consume, facilitated by the Coordinator.

## Development

### Adding a New Node

1.  Create a directory `nodes/koi-net-<your-node-name>-node/`.
2.  Implement the node logic within a Python package (e.g., `your_node_name_node/`).
3.  Define necessary RID types (preferably in the `rid_types` package).
4.  Implement `core.py` (NodeInterface setup), `handlers.py`, `server.py`, `config.py`.
5.  Create `pyproject.toml` and `Dockerfile`.
6.  Add configuration files to `config/docker/` and `config/local/`.
7.  Update the main `docker-compose.yaml` to include the new service.
8.  Update `Makefile` install targets.

### Extending Existing Nodes

Refer to each node's README for specific instructions:

- [Coordinator](nodes/koi-net-coordinator-node/README.md)
- [GitHub Sensor](nodes/koi-net-github-sensor-node/README.md)
- [HackMD Sensor](nodes/koi-net-hackmd-sensor-node/README.md)
- [Processor A - GitHub Indexer](nodes/koi-net-processor-a-node/README.md)
- [Processor B - HackMD Indexer](nodes/koi-net-processor-b-node/README.md)

## Documentation

_(Links to be created/verified)_

- [KOI Protocol Specification](docs/koi-protocol.md)
- [RID Library Documentation](docs/rid-lib.md)
- [Configuration Guide](docs/configuration.md)
- [Docker Deployment](docs/docker.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
