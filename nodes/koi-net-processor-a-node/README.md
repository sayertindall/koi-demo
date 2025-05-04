# Processor A - GitHub Repository Indexer

## Core Logic Overview

This section provides a deep dive into Processor A's implementation details, highlighting the core components and logic that power its functionality.

### 1. Key Constants & Classes

- **`GITHUB_SENSOR_RID`**: Optional configuration parameter that allows specifying a particular GitHub sensor node to connect to, rather than discovering any available GitHub sensor.
- **`GithubCommit`**: The primary RID class that Processor A consumes, representing GitHub commit data.
- **`search_index`**: In-memory structure that maps SHA hashes and keywords to commit information.
- **`KnowledgeSource.External`**: Constants used to indicate the source of knowledge objects during processing.

### 2. How KOI & RID-lib Are Used

#### Node Interface Initialization

```python
node = NodeInterface(
    name="processor-a",
    profile=NodeProfile(
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[],
            state=[]
        ),
        # Consumes GithubCommit implicitly via handlers
    ),
    use_kobj_processor_thread=True,
    first_contact=COORDINATOR_URL,
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=CACHE_DIR,
)
```

#### Registered Event Handlers

1. **Network Handler**: Processes node discovery events

   ```python
   @node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
   def handle_network_discovery(processor: ProcessorInterface, kobj: KnowledgeObject):
       # Handles discovery of Coordinator and GitHub Sensor nodes
   ```

2. **Manifest Handler**: Processes commit manifest events

   ```python
   @node.processor.register_handler(HandlerType.Manifest, rid_types=[GithubCommit])
   def handle_commit_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
       # Handles incoming commit manifests, triggers bundle fetch
   ```

3. **Bundle Handler**: Processes commit bundle data
   ```python
   @node.processor.register_handler(HandlerType.Bundle, rid_types=[GithubCommit])
   def handle_commit_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
       # Processes commit bundle contents and updates the search index
   ```

#### RID-lib Usage

Processor A uses RID-lib for:

- Handling standard KOI-net RIDs (`KoiNetNode`, `KoiNetEdge`)
- Processing GitHub commit RIDs represented as `GithubCommit` classes with `reference` properties
- Automatic bundle dereferencing using the processor's built-in mechanisms

### 3. Proprietary Analysis Logic

The core analysis logic resides in the bundle handler where GitHub commits are indexed:

```python
# Extract message for keyword indexing
message = contents.get("message", "")

# Index by keywords (simple example implementation)
keywords_processed = set()
for keyword in message.lower().split():
    # Basic filtering: length > 3, alphanumeric, avoid duplicates per message
    if len(keyword) > 3 and keyword.isalnum() and keyword not in keywords_processed:
        if keyword not in search_index:
            search_index[keyword] = []
        # Add SHA to keyword list if not already present
        if sha not in search_index[keyword]:
             search_index[keyword].append(sha)
        keywords_processed.add(keyword)
```

The indexing strategy includes:

- Direct SHA-based indexing for exact match lookups
- Keyword extraction from commit messages for content-based search
- Basic filtering rules (length > 3, alphanumeric content)
- Handling of re-indexing situations for updated commits

### 4. Custom Modules & Functions

The node is implemented in a modular structure:

| Module          | Key Functions                  | Purpose                                         |
| --------------- | ------------------------------ | ----------------------------------------------- |
| **core.py**     | `NodeInterface` initialization | Establishes the node's identity and connections |
| **handlers.py** | `handle_network_discovery()`   | Detects Coordinator and GitHub sensor nodes     |
|                 | `handle_commit_manifest()`     | Processes commit manifest events                |
|                 | `handle_commit_bundle()`       | Indexes commit data from bundles                |
|                 | `query_search_index()`         | Implements search functionality                 |
| **server.py**   | `broadcast_events_endpoint()`  | Receives events from other nodes                |
|                 | `search_commits_endpoint()`    | Exposes the search API                          |

#### Search Query Implementation

```python
def query_search_index(query: str) -> list:
    """Queries the in-memory search index."""
    results = []
    query_lower = query.lower()

    # Check if query is a SHA (full or partial)
    if len(query) >= 7:
        # Check full and partial SHA matches
        # ...

    # Check if query is a keyword
    if query_lower in search_index and isinstance(search_index[query_lower], list):
        for sha in search_index[query_lower]:
            # Add keyword matches to results
            # ...

    return results
```

### 5. Configuration & Environment Variables

Key configuration parameters include:

| Parameter           | Default                                                                           | Purpose                      |
| ------------------- | --------------------------------------------------------------------------------- | ---------------------------- |
| `BASE_URL`          | http://{host}:{port}/koi-net                                                      | The node's public endpoint   |
| `COORDINATOR_URL`   | http://coordinator:8080/koi-net (Docker)<br>http://127.0.0.1:8080/koi-net (Local) | The Coordinator node URL     |
| `CACHE_DIR`         | /data/cache (Docker)<br>./.koi/processor-a/cache (Local)                          | Location for cached data     |
| `HOST`              | 0.0.0.0 (Docker)<br>127.0.0.1 (Local)                                             | Interface to bind to         |
| `PORT`              | 8011                                                                              | HTTP server port             |
| `LOG_LEVEL`         | INFO                                                                              | Logging verbosity            |
| `GITHUB_SENSOR_RID` | None                                                                              | Optional specific sensor RID |

The configuration is loaded from YAML files in `config/docker/` or `config/local/` depending on the deployment mode, which is determined by the `KOI_CONFIG_MODE` and `RUN_CONTEXT` environment variables.

### 6. Sample Snippet: Core Processing Flow

The following code shows the complete lifecycle of processing a GitHub commit:

```python
# Step 1: Discover and connect to GitHub sensor
@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handle_network_discovery(processor: ProcessorInterface, kobj: KnowledgeObject):
    # Validate discovered node
    profile = kobj.bundle.validate_contents(NodeProfile)

    # Check if node provides GitHub commits
    provides_github_commits = False
    rid_type_str = "orn:github.commit"
    provides_event = [str(rt) for rt in profile.provides.event if hasattr(profile.provides, 'event')]

    if rid_type_str in provides_event:
        provides_github_commits = True

    # If it's a GitHub sensor, propose an edge to receive commits
    if provides_github_commits:
        logger.info(f"Discovered GitHub Sensor: {kobj.rid}. Proposing edge.")
        edge_bundle = generate_edge_bundle(
            source=kobj.rid,  # Sensor is the source
            target=processor.identity.rid,  # We are the target
            edge_type=EdgeType.WEBHOOK,
            rid_types=[GithubCommit],  # We want GithubCommit events
        )
        processor.handle(bundle=edge_bundle)

# Step 2: Receive commit manifest and request bundle
@node.processor.register_handler(HandlerType.Manifest, rid_types=[GithubCommit])
def handle_commit_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
    rid = kobj.rid
    logger.info(f"Received manifest for commit: {rid.reference}")

    # Request full bundle for indexing
    processor.handle(rid=rid, source=KnowledgeSource.External)

# Step 3: Process commit bundle and update index
@node.processor.register_handler(HandlerType.Bundle, rid_types=[GithubCommit])
def handle_commit_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
    contents = kobj.contents
    sha = contents.get("sha")
    logger.info(f"Processing bundle for commit: {sha[:7]}")

    # Update search index
    message = contents.get("message", "")
    search_index[sha] = message  # Index by full SHA

    # Index by keywords from commit message
    for keyword in message.lower().split():
        if len(keyword) > 3 and keyword.isalnum():
            if keyword not in search_index:
                search_index[keyword] = []
            if sha not in search_index[keyword]:
                search_index[keyword].append(sha)
```

This code demonstrates how Processor A discovers GitHub sensors, establishes connections, receives commit data, and builds its search index - all using the KOI-net protocol's event-driven architecture.

## Overview

The Processor A node is a specialized KOI-net component that consumes GitHub commit data from the GitHub sensor node, builds a searchable index, and provides a search API for querying repository information. It serves as a critical component in the KOI-net knowledge mesh by transforming raw commit data into a queryable knowledge base.

## Features

- Automatically connects to the KOI-net Coordinator and GitHub sensor nodes
- Processes GitHub commit data in real-time
- Maintains an in-memory search index for quick lookup
- Exposes a simple HTTP API for searching indexed commits
- Follows the KOI protocol for data exchange and network operations
- Supports both Docker and local deployment modes

## Architecture

### Network Integration

Processor A establishes bidirectional connections with:

1. **Coordinator Node**: For network discovery and general communication
2. **GitHub Sensor**: To receive GitHub commit events

The node uses the KOI protocol's edge mechanism to establish these connections, with handlers registering for specific Resource ID (RID) types:

```
Coordinator <---> Processor A <--- GitHub Sensor
```

### Data Processing Flow

1. **Discovery**: The network handler detects GitHub sensor nodes on the network
2. **Connection**: Automatically proposes edges to receive GitHub commit events
3. **Manifest Processing**: Receives commit manifests and requests the full bundle
4. **Indexing**: Processes commit bundles to build and maintain a search index
5. **Search API**: Provides endpoint for searching through indexed commits

### Search Index

The search index uses a simple in-memory structure:

```
{
  sha: commit_message,              # Direct SHA lookup
  keyword: [sha1, sha2, ...],       # Keyword to SHAs mapping
  ...
}
```

This enables multiple search capabilities:

- Exact SHA lookups
- Partial SHA matching (≥7 characters)
- Keyword-based search

## API Endpoints

### KOI Protocol Endpoints

- `POST /koi-net/broadcast-events`: Receive events from other nodes
- `POST /koi-net/poll-events`: Provide events to nodes polling this one
- `POST /koi-net/fetch-rids`: Return RIDs matching requested types
- `POST /koi-net/fetch-manifests`: Return manifests for requested RIDs
- `POST /koi-net/fetch-bundles`: Return bundles for requested RIDs
- `GET /koi-net/health`: Check node health status

### Custom Endpoints

- `GET /search?q=<query>`: Search indexed commits
  - Query can be a SHA (full or partial), or keyword
  - Returns matching commit information

## Configuration

### Local Mode

Configuration is loaded from `config/local/processor-a.yaml`:

```yaml
runtime:
  base_url: http://127.0.0.1:8011/koi-net
  cache_dir: ./.koi/processor-a/cache
  host: 127.0.0.1
  log_level: DEBUG
  port: 8011

edges:
  coordinator_url: http://127.0.0.1:8080/koi-net
# Optional: specify a particular GitHub sensor RID
# processor_a:
#   github_sensor_rid: "..."
```

### Docker Mode

When running in Docker, configuration is loaded from `config/docker/processor-a.yaml`:

```yaml
runtime:
  base_url: http://processor-a:8011/koi-net
  cache_dir: /data/cache
  host: 0.0.0.0
  log_level: INFO
  port: 8011

edges:
  coordinator_url: http://coordinator:8080/koi-net
```

## Deployment

### Local Development

1. Ensure the Python dependencies are installed:

   ```
   pip install -e .
   ```

2. Run the node:
   ```
   python -m processor_a_node
   ```

### Docker Deployment

Use Docker Compose to deploy the entire KOI-net system:

```
docker-compose up
```

Or run just this node:

```
docker-compose up processor-a
```

## Development and Extension

The node is designed with the following module structure:

- `__init__.py`: Configures logging
- `__main__.py`: Entry point that starts the node
- `config.py`: Configuration loading and validation
- `core.py`: Core node initialization
- `handlers.py`: Event and data processing handlers
- `server.py`: FastAPI application and endpoint definitions

To extend the search capabilities:

1. Modify the indexing logic in `handlers.py`
2. Update the query implementation in `query_search_index()`
3. Adjust the search endpoint in `server.py` as needed

## Dependencies

- Python 3.12+
- FastAPI and Uvicorn
- KOI-net libraries (v1.0.0b12+)
- RID-lib (v3.2.3+)
- Additional libraries listed in pyproject.toml

## Limitations and Future Work

- The current implementation uses an in-memory index (data is lost on restart)
- Search is limited to SHA and basic keyword matching
- More advanced text analysis could be implemented for better search results
- Persistent storage could be added for the index
