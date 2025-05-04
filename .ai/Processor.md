# Processor Design Specifications

This document outlines the design for Processor A (Repo Indexer) and Processor B (Note Indexer) as described in the PRD.

## ProcessorA – Repo Indexer

### 1. Name & Purpose

**ProcessorA (Repo Indexer):** Subscribes to GitHub sensor manifests, optionally dereferences commit/PR bundles, and maintains a local searchable index via a simple API endpoint.

### 2. KOI-Net Integration

- **NodeInterface:** Initializes a `koi_net.NodeInterface` instance, likely configured as `NodeType.FULL`.
- **Endpoints Exposed:**
  - Implements standard KOI endpoints (`/events/*`, `/edges/*`, `/bundles/*`, `/rids/*`, `/manifests/*`) via `NodeInterface`.
  - Exposes a custom FastAPI endpoint: `GET /search` for querying the local index.
  - Exposes a `/health` endpoint.
- **Edge Management:**
  - On startup, proposes an `EdgeType.WEBHOOK` edge to the Coordinator specified in configuration (`first_contact`).
  - Listens for `KoiNetNode` events to discover the `GitHubSensorNode`.
  - Upon discovering the sensor, proposes a direct `EdgeType.WEBHOOK` edge to it, subscribing to `CommitManifestRID` and potentially `PullRequestManifestRID` events.
- **Event Consumption:** Receives manifests for `CommitManifestRID` (and potentially `PullRequestManifestRID`) via the `/events/broadcast` endpoint from the connected `GitHubSensorNode`.
- **Bundle Fetching:** May optionally use `node.network.request_handler.fetch_bundles` or trigger internal handling via `node.processor.handle(rid=...)` to dereference specific commit/PR RIDs based on manifest content or search needs.

### 3. RID-Lib Integration

- **RID Consumption:** Primarily consumes `CommitManifestRID` (and potentially `PullRequestManifestRID`) via `koi_net.Event` objects.
- **Manifest Handling:** Uses `kobj.manifest` within handlers to inspect metadata (e.g., commit message, author) before deciding whether to dereference.
- **Bundle Handling:** When dereferencing, uses `kobj.bundle.validate_contents()` or accesses `kobj.contents` (dictionary) within bundle handlers to process commit data (SHA, message, author, files changed, etc.).
- **Cache Interaction:** Relies on the underlying `NodeInterface` cache (`CACHE_DIR`) to store fetched bundles. The processor logic itself might implement an additional layer for its searchable index (e.g., in-memory dict, simple file, SQLite).
- **RID Emission:** **Does not emit any new RIDs** as per the PRD simplification note.

### 4. Inputs & Outputs

- **Inputs:**
  - `koi_net.Event` objects containing manifests for:
    - `github_sensor_node.types.GithubCommit` (via `CommitManifestRID`)
    - _(Potentially)_ A corresponding `PullRequestManifestRID` (definition needed if used).
  - HTTP GET requests to its custom `/search` endpoint.
- **Outputs:**
  - HTTP JSON responses from its custom `/search` endpoint (structure TBD, e.g., `{"results": [{"rid": "...", "match_context": "..."}]}`).
  - Standard KOI protocol responses from its `NodeInterface` endpoints.
  - **No new `koi_net.Event` objects or RIDs are broadcast.**

### 5. Internal Flow

1.  Initialize `NodeInterface` with profile specifying consumption of `GithubCommit` RIDs.
2.  Register event handlers (`@node.processor.register_handler`) for:
    - `HandlerType.Network` for `KoiNetNode` (to discover Coordinator and Sensor).
    - `HandlerType.Manifest` for `CommitManifestRID` (and potentially `PullRequestManifestRID`).
    - `HandlerType.Bundle` for `CommitManifestRID` (and potentially `PullRequestManifestRID`) if dereferencing.
3.  Start the `NodeInterface` (`node.start()`). This automatically attempts connection to the `first_contact` Coordinator.
4.  **Coordinator Handshake:** Handler proposes edge back to Coordinator upon discovery.
5.  **Sensor Discovery & Handshake:** Handler discovers `GitHubSensorNode` (filtering by profile/provided RIDs), proposes edge, and accepts incoming edge proposal from the sensor.
6.  **Manifest Processing:** The manifest handler receives `CommitManifestRID` events.
    - Filters events based on relevance (e.g., specific branches - though not specified in PRD).
    - Decides whether to dereference the bundle based on manifest data (e.g., keywords in message) or if indexing requires full content.
    - If dereferencing, calls `node.processor.handle(rid=manifest.rid, source=KnowledgeSource.External)` to trigger bundle fetch and processing by the bundle handler.
7.  **Bundle Processing (if dereferenced):** The bundle handler receives the commit contents.
    - Extracts relevant data (SHA, message, author, timestamp, etc.).
    - Updates the internal searchable index (implementation specific - e.g., add keywords/SHA to an in-memory dictionary or a simple file).
8.  **Search API:** A separate FastAPI route (`/search`) handles incoming GET requests.
    - Parses the query parameter (`q`).
    - Searches the internal index based on the query (e.g., lookup SHA, search keywords).
    - Returns matching results as JSON.

### 6. Configuration

- **YAML (`config/processor-a.yaml`):**
  - `runtime.base_url`: (String, Required) Public URL of this processor node (e.g., `http://processor-a:8011/koi-net`).
  - `runtime.host`: (String, Default: "0.0.0.0") Host to bind the FastAPI server.
  - `runtime.port`: (Integer, Default: 8011) Port to bind the FastAPI server.
  - `runtime.log_level`: (String, Default: "INFO") Logging level.
  - `runtime.cache_dir`: (String, Required) Path to the shared RID cache volume (e.g., `/data/cache`).
  - `edges.coordinator_url`: (String, Required) URL of the Coordinator node (e.g., `http://coordinator:8080/koi-net`).
  - _(Optional)_ `processor_a.github_sensor_rid`: (String, Optional) Specific RID of the GitHub sensor to connect to (if discovery is bypassed).
- **Environment (`config/global.env`):**
  - No specific ENV variables required by Processor A itself identified yet, but inherits shared settings if needed.

### 7. Sample Snippets

```python
# processor_a/core.py (Example Node Setup)
import os
import logging
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
# Assuming GithubCommit is defined elsewhere accessible to the processor
from github_sensor_node.types import GithubCommit # May need to be in shared lib
# Import config values
from .config import BASE_URL, COORDINATOR_URL, CACHE_DIR

logger = logging.getLogger(__name__)
name = "processor-a"
identity_dir = f".koi/{name}"
os.makedirs(identity_dir, exist_ok=True)

node = NodeInterface(
    name=name,
    profile=NodeProfile(
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides( # Processor A provides no new RIDs
             event=[], state=[]
        )
        # Consumes defined implicitly by handlers or explicitly if needed
    ),
    use_kobj_processor_thread=True,
    first_contact=COORDINATOR_URL,
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=CACHE_DIR,
)

# ---

# processor_a/handlers.py (Example Manifest Handler)
from .core import node
from koi_net.processor import ProcessorInterface, HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from github_sensor_node.types import GithubCommit # Assumed shared/accessible

logger = logging.getLogger(__name__)

# In-memory index example
search_index = {} # {sha: commit_message, keyword: [sha1, sha2]}

@node.processor.register_handler(HandlerType.Manifest, rid_types=[GithubCommit])
def handle_commit_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
    manifest = kobj.manifest
    rid: GithubCommit = manifest.rid
    logger.info(f"Received manifest for commit: {rid.reference}")

    # Example: Always dereference for indexing message content
    logger.debug(f"Requesting bundle for {rid} for indexing.")
    processor.handle(rid=rid, source=KnowledgeSource.External) # Trigger bundle fetch

# ---

# processor_a/handlers.py (Example Bundle Handler)
@node.processor.register_handler(HandlerType.Bundle, rid_types=[GithubCommit])
def handle_commit_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
     if not kobj.contents:
         logger.warning(f"Bundle for {kobj.rid} has no contents.")
         return

     rid: GithubCommit = kobj.rid
     contents = kobj.contents
     logger.info(f"Processing bundle for commit: {rid.sha[:7]}")

     # Update simple index (example)
     message = contents.get("message", "")
     search_index[rid.sha] = message # Index by SHA
     # Simple keyword indexing
     for keyword in message.lower().split():
         if len(keyword) > 3: # Basic filtering
             if keyword not in search_index:
                 search_index[keyword] = []
             if rid.sha not in search_index[keyword]:
                  search_index[keyword].append(rid.sha)

# ---

# processor_a/server.py (Example Search Endpoint)
from fastapi import FastAPI, HTTPException
from .core import node # Assuming node and app setup like template
from .handlers import search_index # Import the example index

# app = FastAPI(...) # Assuming FastAPI app setup elsewhere

@app.get("/search")
async def search_commits(q: str):
    logger.info(f"Received search request: q='{q}'")
    results = []
    query = q.lower()

    # Simple search logic (example)
    if len(query) >= 7 and query in search_index: # Check if it's a SHA
        results.append({"rid": f"orn:github.commit:{query}", "match_context": search_index.get(query, "")})
    elif query in search_index and isinstance(search_index[query], list): # Check keywords
         for sha in search_index[query]:
             # Need owner/repo - this index example is too simple
             # Need a better index like {sha: {"rid": rid_obj, "message": msg}}
             # For now, just return SHA
             results.append({"sha": sha, "match_context": "Keyword match"})
    else:
         # More sophisticated search could go here
         pass

    if not results:
        logger.info(f"No results found for query: '{q}'")
        # Return 404 or empty list? Let's use empty list.
        # raise HTTPException(status_code=404, detail="No matching commits found")
    return {"query": q, "results": results}
```

---

## ProcessorB – Note Indexer

### 1. Name & Purpose

**ProcessorB (Note Indexer):** Subscribes to HackMD sensor manifests, dereferences note bundles, and maintains a local searchable index of Markdown content via a simple API endpoint.

### 2. KOI-Net Integration

- **NodeInterface:** Initializes a `koi_net.NodeInterface` instance, likely configured as `NodeType.FULL`.
- **Endpoints Exposed:**
  - Implements standard KOI endpoints via `NodeInterface`.
  - Exposes a custom FastAPI endpoint: `GET /search` for querying the local index.
  - Exposes a `/health` endpoint.
- **Edge Management:**
  - On startup, proposes an `EdgeType.WEBHOOK` edge to the Coordinator.
  - Listens for `KoiNetNode` events to discover the `HackMDSensorNode`.
  - Upon discovering the sensor, proposes a direct `EdgeType.WEBHOOK` edge to it, subscribing to `HackMDNote` events.
  - _(Optional/Future based on PRD conflict):_ Discovers `ProcessorA` and negotiates a direct `EdgeType.KNOWLEDGE` edge to potentially exchange derived RIDs (like `RiskScoreRID` -> `ActionItemRID`).
- **Event Consumption:** Receives manifests for `HackMDNote` via `/events/broadcast` from the connected `HackMDSensorNode`.
- **Bundle Fetching:** Always uses `node.processor.handle(rid=...)` or `node.network.request_handler.fetch_bundles` upon receiving a manifest to dereference the full note content for indexing.

### 3. RID-Lib Integration

- **RID Consumption:** Consumes `HackMDNote` RIDs (defined in `hackmd_sensor_node/rid_types.py`) via `koi_net.Event` objects.
- **Manifest Handling:** Uses `kobj.manifest` primarily to trigger bundle dereferencing. May check timestamp against local state if implementing update logic vs. re-indexing all the time.
- **Bundle Handling:** Uses `kobj.bundle.validate_contents()` or accesses `kobj.contents` to get the full Markdown content, title, tags, and metadata (`lastChangedAt`, etc.).
- **Cache Interaction:** Relies on the `NodeInterface` cache (`CACHE_DIR`) for bundle storage. Implements its own searchable index (e.g., in-memory dict mapping tags/title words to note IDs).
- **RID Emission:** **Does not emit any new RIDs** as per the PRD simplification note. _(Note: This contradicts the PRD Table 4 mention of emitting `ActionItemRID` linked to `RiskScoreRID`. The simplification note takes precedence for this initial design)._

### 4. Inputs & Outputs

- **Inputs:**
  - `koi_net.Event` objects containing manifests for `hackmd_sensor_node.rid_types.HackMDNote`.
  - HTTP GET requests to its custom `/search` endpoint.
- **Outputs:**
  - HTTP JSON responses from its custom `/search` endpoint (structure TBD, e.g., `{"results": [{"rid": "...", "title": "...", "tags": [...]}]}`).
  - Standard KOI protocol responses from its `NodeInterface` endpoints.
  - **No new `koi_net.Event` objects or RIDs are broadcast.**

### 5. Internal Flow

1.  Initialize `NodeInterface` with profile specifying consumption of `HackMDNote` RIDs.
2.  Register event handlers (`@node.processor.register_handler`) for:
    - `HandlerType.Network` for `KoiNetNode` (to discover Coordinator and Sensor, potentially Processor A).
    - `HandlerType.Manifest` for `HackMDNote`.
    - `HandlerType.Bundle` for `HackMDNote`.
3.  Start the `NodeInterface` (`node.start()`).
4.  **Coordinator Handshake:** Handler proposes edge back to Coordinator.
5.  **Sensor Discovery & Handshake:** Handler discovers `HackMDSensorNode`, proposes edge, and accepts incoming edge proposal.
6.  **Manifest Processing:** The manifest handler receives `HackMDNote` events.
    - Immediately triggers bundle dereferencing via `node.processor.handle(rid=manifest.rid, source=KnowledgeSource.External)`.
7.  **Bundle Processing:** The bundle handler receives the full note contents.
    - Extracts `title`, `tags`, `content`, `lastChangedAt` from `kobj.contents`.
    - _(Optional)_ Compare `lastChangedAt` with locally stored timestamp for this note ID to avoid re-processing unchanged notes.
    - Parses Markdown content (implementation specific - e.g., simple regex for tags/titles, or more complex parsing for action items if that feature were included).
    - Updates the internal searchable index (e.g., add note ID to lists associated with tags, index words in the title).
    - _(Optional/Future)_ If knowledge edge with Processor A exists, potentially query Processor A based on parsed content.
8.  **Search API:** A separate FastAPI route (`/search`) handles incoming GET requests.
    - Parses the query parameter (`q`).
    - Searches the internal index based on the query (e.g., lookup notes by tag, search title keywords).
    - Returns matching results (e.g., list of note RIDs and titles) as JSON.

### 6. Configuration

- **YAML (`config/processor-b.yaml`):**
  - `runtime.base_url`: (String, Required) Public URL of this processor node (e.g., `http://processor-b:8012/koi-net`).
  - `runtime.host`: (String, Default: "0.0.0.0") Host to bind the FastAPI server.
  - `runtime.port`: (Integer, Default: 8012) Port to bind the FastAPI server.
  - `runtime.log_level`: (String, Default: "INFO") Logging level.
  - `runtime.cache_dir`: (String, Required) Path to the shared RID cache volume (e.g., `/data/cache`).
  - `edges.coordinator_url`: (String, Required) URL of the Coordinator node (e.g., `http://coordinator:8080/koi-net`).
  - _(Optional)_ `processor_b.hackmd_sensor_rid`: (String, Optional) Specific RID of the HackMD sensor to connect to.
- **Environment (`config/global.env`):**
  - No specific ENV variables required by Processor B itself identified yet.

### 7. Sample Snippets

```python
# processor_b/core.py (Example Node Setup)
import os
import logging
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
# Import the RID type
from hackmd_sensor_node.rid_types import HackMDNote
# Import config values
from .config import BASE_URL, COORDINATOR_URL, CACHE_DIR

logger = logging.getLogger(__name__)
name = "processor-b"
identity_dir = f".koi/{name}"
os.makedirs(identity_dir, exist_ok=True)

node = NodeInterface(
    name=name,
    profile=NodeProfile(
        base_url=BASE_URL,
        node_type=NodeType.FULL,
        provides=NodeProvides( # Processor B provides no new RIDs per simplification
             event=[], state=[]
        )
    ),
    use_kobj_processor_thread=True,
    first_contact=COORDINATOR_URL,
    identity_file_path=os.path.abspath(f"{identity_dir}/{name}_identity.json"),
    event_queues_file_path=os.path.abspath(f"{identity_dir}/{name}_event_queues.json"),
    cache_directory_path=CACHE_DIR,
)

# ---

# processor_b/handlers.py (Example Manifest Handler)
from .core import node
from koi_net.processor import ProcessorInterface, HandlerType
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from hackmd_sensor_node.rid_types import HackMDNote

logger = logging.getLogger(__name__)

# In-memory index example
# { "tag": [rid1, rid2], "title_word": [rid1, rid3], ... }
# { rid_str: {"title": title, "tags": tags, "lastChangedAt": ts}}
search_index = {}
note_metadata = {}

@node.processor.register_handler(HandlerType.Manifest, rid_types=[HackMDNote])
def handle_note_manifest(processor: ProcessorInterface, kobj: KnowledgeObject):
    manifest = kobj.manifest
    rid: HackMDNote = manifest.rid
    logger.info(f"Received manifest for HackMD note: {rid.reference}")

    # Always dereference notes for indexing
    logger.debug(f"Requesting bundle for {rid} for indexing.")
    processor.handle(rid=rid, source=KnowledgeSource.External) # Trigger bundle fetch

# ---

# processor_b/handlers.py (Example Bundle Handler)
# (Requires markdown parsing library, e.g., markdown-it-py or similar)
# import re # Example for simple parsing

@node.processor.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
def handle_note_bundle(processor: ProcessorInterface, kobj: KnowledgeObject):
     if not kobj.contents:
         logger.warning(f"Bundle for {kobj.rid} has no contents.")
         return

     rid: HackMDNote = kobj.rid
     contents = kobj.contents
     rid_str = str(rid) # Use string representation for dict keys

     logger.info(f"Processing bundle for note: {rid.note_id} - '{contents.get('title', 'N/A')}'")

     # Check timestamp to avoid re-indexing if not changed
     last_changed = contents.get("lastChangedAt")
     if rid_str in note_metadata and last_changed == note_metadata[rid_str].get("lastChangedAt"):
         logger.debug(f"Note {rid.note_id} has not changed since last index. Skipping.")
         return

     # --- Update Metadata Cache ---
     note_metadata[rid_str] = {
         "title": contents.get("title", ""),
         "tags": contents.get("tags", []),
         "lastChangedAt": last_changed
     }

     # --- Update Search Index (Example: Tags and Title words) ---
     # Clear old index entries for this note first (important for updates)
     for key, rid_list in list(search_index.items()):
         if rid_str in rid_list:
             search_index[key].remove(rid_str)
             if not search_index[key]: # Remove key if list becomes empty
                 del search_index[key]

     # Index by tags
     tags = contents.get("tags", [])
     for tag in tags:
         tag_key = tag.lower()
         if tag_key not in search_index:
             search_index[tag_key] = []
         if rid_str not in search_index[tag_key]:
              search_index[tag_key].append(rid_str)

     # Index by title words
     title = contents.get("title", "")
     for word in title.lower().split():
         if len(word) > 2: # Basic filtering
             if word not in search_index:
                 search_index[word] = []
             if rid_str not in search_index[word]:
                 search_index[word].append(rid_str)

     # Index by note ID itself
     search_index[rid.note_id] = [rid_str]


     # Note: Markdown content parsing is omitted for brevity
     # md_content = contents.get("content", "")
     # Parse md_content here...

     logger.debug(f"Updated index for note {rid.note_id}")

# ---

# processor_b/server.py (Example Search Endpoint)
from fastapi import FastAPI, HTTPException
from .core import node # Assuming node and app setup like template
from .handlers import search_index, note_metadata # Import example index/metadata

# app = FastAPI(...) # Assuming FastAPI app setup elsewhere

@app.get("/search")
async def search_notes(q: str):
    logger.info(f"Received note search request: q='{q}'")
    results_rids = set()
    query = q.lower()

    # Simple search logic (example: match query as tag or title word or note_id)
    if query in search_index:
        results_rids.update(search_index[query])

    # Format results
    results = []
    for rid_str in results_rids:
        meta = note_metadata.get(rid_str, {})
        results.append({
            "rid": rid_str,
            "title": meta.get("title", "N/A"),
            "tags": meta.get("tags", [])
        })

    if not results:
        logger.info(f"No results found for query: '{q}'")

    return {"query": q, "results": results}



```
