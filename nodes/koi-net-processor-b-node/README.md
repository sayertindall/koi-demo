# Processor B - HackMD Note Indexer

## Core Logic Overview

This section provides an in-depth look at Processor B's implementation details, highlighting the key components and logic that drive its note indexing functionality.

### 1. Key Constants & Classes

- **`HACKMD_SENSOR_RID`**: Optional configuration parameter that allows specifying a particular HackMD sensor node to connect to, instead of auto-discovering available HackMD sensors.
- **`HackMDNote`**: The primary RID class that Processor B consumes, representing HackMD note data.
- **`search_index`**: In-memory structure that maps search terms (tags, title words, note IDs) to matching note RIDs.
- **`note_metadata`**: In-memory cache that stores metadata for indexed notes to avoid re-indexing unchanged content and enrich search results.

### 2. How KOI & RID-lib Are Used

#### Node Interface Initialization

```python
node = NodeInterface(
    name="processor-b",
    profile=NodeProfile(
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[],
            state=[]
        ),
        # Consumes HackMDNote implicitly via handlers
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
       # Handles discovery of Coordinator and HackMD Sensor nodes
   ```

2. **Manifest Handler**: Processes note manifest events

   ```python
   @node.processor.register_handler(HandlerType.Manifest, rid_types=[HackMDNote])
   def handle_note_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
       # Handles incoming note manifests, triggers bundle fetch
   ```

3. **Bundle Handler**: Processes note bundle data
   ```python
   @node.processor.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
   def handle_note_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
       # Processes note bundle contents and updates the search index
   ```

#### RID-lib Usage

Processor B uses RID-lib for:

- Handling standard KOI-net RIDs (`KoiNetNode`, `KoiNetEdge`)
- Processing HackMD note RIDs represented as `HackMDNote` classes with `note_id` properties
- Automatic bundle dereferencing using the processor's built-in mechanisms
- RID string conversion for indexing: `rid_str = str(rid)`

### 3. Proprietary Analysis Logic

The core analysis logic centers around efficient note indexing and change detection:

```python
# Check if note has changed since last indexing
last_changed = contents.get("lastChangedAt")
if rid_str in note_metadata and last_changed == note_metadata[rid_str].get("lastChangedAt"):
    logger.debug(f"Note {note_id} has not changed ({last_changed}) since last index. Skipping.")
    return

# Update metadata cache
current_tags = contents.get("tags", [])
note_metadata[rid_str] = {
    "title": title,
    "tags": current_tags,
    "lastChangedAt": last_changed
}

# Index by tags (critical for topic-based search)
for tag in current_tags:
    tag_key = tag.lower()  # Case-insensitive tag indexing
    if tag_key not in search_index:
        search_index[tag_key] = []
    if rid_str not in search_index[tag_key]:
        search_index[tag_key].append(rid_str)

# Index by title words (enables title-based discovery)
for word in title.lower().split():
    if len(word) > 2:  # Basic filtering
        if word not in search_index:
            search_index[word] = []
        if rid_str not in search_index[word]:
            search_index[word].append(rid_str)
```

The indexing strategy includes:

- Change detection using `lastChangedAt` timestamps to avoid redundant processing
- Tag-based indexing for topical organization and search
- Title word indexing for content relevance
- Direct note ID indexing for exact lookups
- Metadata caching for enriched search results

### 4. Custom Modules & Functions

The node is implemented with the following modular structure:

| Module          | Key Functions                  | Purpose                                     |
| --------------- | ------------------------------ | ------------------------------------------- |
| **core.py**     | `NodeInterface` initialization | Establishes node identity and connections   |
| **handlers.py** | `handle_network_discovery()`   | Detects Coordinator and HackMD sensor nodes |
|                 | `handle_note_manifest()`       | Processes note manifest events              |
|                 | `handle_note_bundle()`         | Indexes note data from bundles              |
|                 | `query_note_index()`           | Implements search functionality             |
| **server.py**   | `broadcast_events_endpoint()`  | Receives events from other nodes            |
|                 | `search_notes_endpoint()`      | Exposes the search API                      |

#### Search Query Implementation

```python
def query_note_index(query: str) -> list:
    """Queries the in-memory note search index."""
    results_rids = set()  # Use a set to automatically handle duplicates
    query_lower = query.lower()

    # 1. Check if query is a direct Note ID match
    if query in search_index and isinstance(search_index[query], list):
         results_rids.update(search_index[query])

    # 2. Check if query matches a tag (case-insensitive)
    if query_lower in search_index and isinstance(search_index[query_lower], list):
        results_rids.update(search_index[query_lower])

    # 3. Check if query matches a title word (case-insensitive)
    if query_lower in search_index and isinstance(search_index[query_lower], list):
        results_rids.update(search_index[query_lower])

    # Format results using metadata cache for rich responses
    results = []
    for rid_str in results_rids:
        meta = note_metadata.get(rid_str, {})
        results.append({
            "rid": rid_str,
            "title": meta.get("title", "N/A"),
            "tags": meta.get("tags", [])
        })

    # Sort results alphabetically by title
    results.sort(key=lambda x: x.get("title", "").lower())

    return results
```

### 5. Configuration & Environment Variables

Key configuration parameters include:

| Parameter           | Default                                                                           | Purpose                      |
| ------------------- | --------------------------------------------------------------------------------- | ---------------------------- |
| `BASE_URL`          | http://{host}:{port}/koi-net                                                      | The node's public endpoint   |
| `COORDINATOR_URL`   | http://coordinator:8080/koi-net (Docker)<br>http://127.0.0.1:8080/koi-net (Local) | The Coordinator node URL     |
| `CACHE_DIR`         | /data/cache (Docker)<br>./.koi/processor-b/cache (Local)                          | Location for cached data     |
| `HOST`              | 0.0.0.0 (Docker)<br>127.0.0.1 (Local)                                             | Interface to bind to         |
| `PORT`              | 8012                                                                              | HTTP server port             |
| `LOG_LEVEL`         | INFO                                                                              | Logging verbosity            |
| `HACKMD_SENSOR_RID` | None                                                                              | Optional specific sensor RID |

The configuration is loaded from YAML files in `config/docker/` or `config/local/` depending on the deployment mode, which is controlled by the `KOI_CONFIG_MODE` and `RUN_CONTEXT` environment variables.

### 6. Sample Snippet: Core Processing Flow

The following code demonstrates the complete lifecycle of processing a HackMD note:

```python
# Step 1: Discover and connect to HackMD sensor
@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handle_network_discovery(processor: ProcessorInterface, kobj: KnowledgeObject):
    # Validate discovered node
    profile = kobj.bundle.validate_contents(NodeProfile)

    # Check if the node provides HackMD notes
    provides_hackmd_notes = False
    if HackMDNote in profile.provides.event or HackMDNote in profile.provides.state:
        provides_hackmd_notes = True

    # If it's a HackMD sensor, propose an edge to receive notes
    if provides_hackmd_notes:
        # Check if we're configured to use a specific sensor
        if HACKMD_SENSOR_RID and str(kobj.rid) != HACKMD_SENSOR_RID:
            logger.debug(f"Discovered HackMD sensor {kobj.rid}, but configured to connect only to {HACKMD_SENSOR_RID}. Ignoring.")
            return

        logger.info(f"Discovered HackMD Sensor: {kobj.rid}. Proposing edge.")
        edge_bundle = generate_edge_bundle(
            source=kobj.rid,  # Sensor is the source
            target=processor.identity.rid,  # We are the target
            edge_type=EdgeType.WEBHOOK,
            rid_types=[HackMDNote],  # We want HackMDNote events
        )
        processor.handle(bundle=edge_bundle)

# Step 2: Receive note manifest and request bundle
@node.processor.register_handler(HandlerType.Manifest, rid_types=[HackMDNote])
def handle_note_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
    rid = kobj.rid
    logger.info(f"Received manifest for HackMD note: {rid.note_id}")

    # Request full bundle for indexing
    processor.handle(rid=rid, source=KnowledgeSource.External)

# Step 3: Process note bundle and update index
@node.processor.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
def handle_note_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
    rid = kobj.rid
    contents = kobj.contents
    rid_str = str(rid)
    note_id = rid.note_id
    title = contents.get("title", f"Note {note_id}")

    logger.info(f"Processing bundle for note: {note_id} - '{title}'")

    # Skip unchanged notes using timestamp comparison
    last_changed = contents.get("lastChangedAt")
    if rid_str in note_metadata and last_changed == note_metadata[rid_str].get("lastChangedAt"):
        return

    # Update metadata and index the note
    current_tags = contents.get("tags", [])
    note_metadata[rid_str] = {
        "title": title,
        "tags": current_tags,
        "lastChangedAt": last_changed
    }

    # Index by tags, title words, and note ID
    # ... [indexing logic as shown earlier] ...
```

This code demonstrates how Processor B discovers HackMD sensors, establishes connections, receives note data, and builds its search index - all within the KOI-net protocol's event-driven architecture.

## Overview

The Processor B node is a specialized KOI-net component that consumes HackMD note data from the HackMD sensor node, constructs a comprehensive search index, and provides a search API for discovering and retrieving notes. As an integral part of the KOI-net knowledge mesh, it transforms raw note data into an easily searchable knowledge repository.

## Features

- Seamlessly connects to the KOI-net Coordinator and HackMD sensor nodes
- Processes HackMD note data as it arrives
- Builds a multi-faceted search index based on note metadata
- Offers a simple HTTP API for searching through indexed notes
- Fully implements the KOI protocol for network operations
- Supports both Docker and local deployment configurations

## Architecture

### Network Integration

Processor B establishes and maintains connections with:

1. **Coordinator Node**: For network discovery and mesh communication
2. **HackMD Sensor**: To receive HackMD note events and updates

The node leverages the KOI protocol's edge mechanism to establish these connections, automatically registering for the relevant Resource ID (RID) types:

```
Coordinator <---> Processor B <--- HackMD Sensor
```

### Data Processing Flow

1. **Network Discovery**: The network handler identifies HackMD sensor nodes
2. **Edge Establishment**: Automatically proposes edges to receive note events
3. **Manifest Processing**: Receives note manifests and requests full bundle data
4. **Index Construction**: Processes note bundles to build and update the search index
5. **Search Service**: Provides endpoints for querying the indexed notes

### Search Index Structure

The search index uses a dual in-memory structure:

```python
# Map search terms to matching RIDs
search_index = {
    "tag": [rid_str1, rid_str2],         # Tag-based lookup
    "title_word": [rid_str1, rid_str3],  # Title word lookup
    "note_id": [rid_str]                 # Direct ID lookup
}

# Store note metadata for rich search results
note_metadata = {
    rid_str: {
        "title": "Note Title",
        "tags": ["tag1", "tag2"],
        "lastChangedAt": timestamp
    }
}
```

This enables multiple search capabilities:

- Tag-based search
- Title word search
- Direct note ID lookup
- Change tracking to avoid reindexing unchanged notes

## API Endpoints

### KOI Protocol Endpoints

- `POST /koi-net/broadcast-events`: Receive events from other nodes
- `POST /koi-net/poll-events`: Provide events to nodes polling this one
- `POST /koi-net/fetch-rids`: Return RIDs matching requested types
- `POST /koi-net/fetch-manifests`: Return manifests for requested RIDs
- `POST /koi-net/fetch-bundles`: Return bundles for requested RIDs
- `GET /koi-net/health`: Check node health status

### Custom Endpoints

- `GET /search?q=<query>`: Search indexed notes
  - Query can be a note ID, tag, or word from a note title
  - Returns matching notes with titles and tags

## Configuration

### Local Mode

Configuration is loaded from `config/local/processor-b.yaml`:

```yaml
runtime:
  base_url: http://127.0.0.1:8012/koi-net
  cache_dir: ./.koi/processor-b/cache
  host: 127.0.0.1
  log_level: DEBUG
  port: 8012

edges:
  coordinator_url: http://127.0.0.1:8080/koi-net
# Optional: specify a particular HackMD sensor
# processor_b:
#   hackmd_sensor_rid: "..."
```

### Docker Mode

When running in Docker, configuration is loaded from `config/docker/processor-b.yaml`:

```yaml
runtime:
  base_url: http://processor-b:8012/koi-net
  cache_dir: /data/cache
  host: 0.0.0.0
  log_level: INFO
  port: 8012

edges:
  coordinator_url: http://coordinator:8080/koi-net
```

## Deployment

### Local Development

1. Install the required dependencies:

   ```
   pip install -e .
   ```

2. Start the node:
   ```
   python -m processor_b_node
   ```

### Docker Deployment

Use Docker Compose to deploy the entire KOI-net system:

```
docker-compose up
```

Or run only this specific node:

```
docker-compose up processor-b
```

## Development and Extension

The node follows a modular structure:

- `__init__.py`: Logging configuration
- `__main__.py`: Entry point for node execution
- `config.py`: Configuration loading and environment setup
- `core.py`: KOI-net node initialization
- `handlers.py`: Event processing and index management
- `server.py`: FastAPI application and endpoints

To enhance search capabilities:

1. Extend the indexing logic in `handlers.py`
2. Modify the query implementation in `query_note_index()`
3. Enhance the search endpoint response in `server.py`

Current indexing is based on:

- Note IDs (direct lookup)
- Tags (keyword categorization)
- Title words (content relevance)

## Dependencies

- Python 3.12+
- FastAPI and Uvicorn
- KOI-net libraries (v1.0.0b12+)
- RID-lib (v3.2.3+)
- Additional dependencies as listed in pyproject.toml

## Limitations and Future Work

- Current implementation uses in-memory storage (no persistence between restarts)
- Full-text search of note content is not implemented but could be added
- No pagination for search results (returns all matches)
- Could be extended with:
  - Persistent storage for the index
  - Advanced text analysis (stemming, entity extraction)
  - Support for more complex query syntax
  - Note content parsing and keyword extraction
