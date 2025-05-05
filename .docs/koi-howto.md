# KOI‑net – Complete Repository Reference

**Repository:** `blockscience/koi-net`

---

## 1. Purpose & Scope

KOI‑net is the reference Python implementation of the **KOI‑net protocol**—a lightweight, RID‑based messaging layer that lets autonomous "knowledge nodes" discover each other, exchange state (RIDs, Manifests, Bundles) and coordinate updates via event broadcasts. It builds directly on [`rid‑lib`](https://github.com/BlockScience/rid-lib) and provides:

- Typed RIDs for nodes (`KoiNetNode`) & edges (`KoiNetEdge`)
- Five JSON endpoints for event & state transfer
- A pluggable knowledge‑processing pipeline with decorator‑driven handlers
- Local cache & P2P fetch helpers

---

## 2. High‑Level Architecture

```text
src/koi_net/
├── core.py          ⟶ NodeInterface façade (cache, network, processor)
├── config.py        ⟶ YAML / .env driven runtime config
├── identity.py      ⟶ Generates & stores node RID / profile / bundle
├── network/         ⟶ P2P comms (graph view + HTTP helpers)
│   ├── graph.py     ⟶ NetworkX DG wrapper (nodes, edges, profiles)
│   ├── interface.py ⟶ Event queues & high‑level orchestration
│   ├── request_handler.py  ⟶ HTTP POST client (FastAPI‑agnostic)
│   └── response_handler.py ⟶ Generate payloads for incoming requests
├── processor/       ⟶ Knowledge pipeline (RID→Manifest→Bundle→Network→Final)
│   ├── interface.py ⟶ Queue + worker thread + pipeline runner
│   ├── handler.py   ⟶ `KnowledgeHandler` decorator + `STOP_CHAIN` logic
│   ├── knowledge_object.py ⟶ Normalised container used in pipeline
│   └── default_handlers.py ⟶ 4 default handlers (RID, Manifest, Bundle, Network)
├── protocol/        ⟶ Pure data layer (pydantic models & constants)
│   ├── api_models.py  ⟶ Request / response schemas
│   ├── consts.py      ⟶ API paths
│   ├── node.py        ⟶ `NodeProfile`, `NodeType`, `NodeProvides`
│   ├── edge.py        ⟶ `EdgeProfile`, `EdgeType`, `EdgeStatus`
│   ├── event.py       ⟶ `Event`, `EventType`
│   └── helpers.py     ⟶ `generate_edge_bundle(...)`
└── __init__.py       ⟶ Re‑exports `NodeInterface`
```

### Supporting files

- **`koi-net-protocol-openapi.json`** – generated OpenAPI 3.1 spec for FastAPI servers.
- **Examples folder** – runnable reference nodes (`basic_coordinator_node.py`, partial/full templates).
- **`pyproject.toml` + `requirements.txt`** – package metadata & deps.
- **GitHub workflow** – auto‑publish to PyPI + Sigstore signing.

---

## 3. Installation Matrix

| Use‑case           | Command                         |
| ------------------ | ------------------------------- |
| Library only       | `pip install koi-net`           |
| Examples (FastAPI) | `pip install koi-net[examples]` |
| Dev / release      | `pip install -e .[dev]`         |

Python ≥ 3.10 is required; `rid‑lib >= 3.2.1`, `networkx`, `httpx`, `pydantic` are core deps.

---

## 4. Core Concepts & Data Types

| Concept               | RID Type / Model  | Stored Where                  | Notes                                                     |
| --------------------- | ----------------- | ----------------------------- | --------------------------------------------------------- |
| **Node**              | `KoiNetNode`      | Local cache ➝ bundle(profile) | Contains `NodeProfile` (base‑URL, provides list, type)    |
| **Edge**              | `KoiNetEdge`      | Bundle(`EdgeProfile`)         | Directed; status `PROPOSED/APPROVED`; type `WEBHOOK/POLL` |
| **Event**             | pydantic `Event`  | Transient (queues)            | Types: `NEW`, `UPDATE`, `FORGET` (“FUN”)                  |
| **Manifest / Bundle** | `rid-lib` objects | Cache directories             | Hash + timestamp integrity                                |

## http://0.0.0.0:8080

## 5. Configuration (`koi_net.config`)

```yaml
server:
  host: 127.0.0.1
  port: 8000
  path: /koi-net
koi_net:
  node_name: mynode
  node_profile:
    node_type: FULL|PARTIAL
    provides:
      event: [] # RID types broadcasted
      state: [] # RID types served via fetch*
  cache_directory_path: .rid_cache
  event_queues_path: event_queues.json
  first_contact: http://seed-node/koi-net
```

`Config.load_from_yaml()` auto‑fills missing fields & persists defaults.

---

## 6. Node Lifecycle (`NodeInterface`)

1. **Init** – wires `Cache`, `NodeIdentity`, `NetworkInterface`, `ProcessorInterface`.
2. **start()**

   - spin worker thread (if enabled)
   - load persisted event queues
   - regen in‑memory graph
   - enqueue own bundle (`NEW`)
   - optional handshake with `first_contact`.

3. **stop()** – flush pipeline, persist queues.

---

## 7. Processor Pipeline (`processor.interface`)

```
RID ⇒ Manifest ⇒ Bundle ⇒ [cache write/delete] ⇒ Network ⇒ Final
```

Each stage triggers a **handler chain** (ordered list). Handlers are `KnowledgeHandler` objects created via decorator:

```python
@node.processor.register_handler(HandlerType.Bundle)
def my_logic(proc, kobj):
    ...
```

Return contract:

- `None` – pass unchanged kobj to next handler.
- Modified `KnowledgeObject` – continue with new kobj.
- `STOP_CHAIN` – abort remaining handlers + downstream stages.

### Default handlers (summary)

| Stage    | Function                      | Behaviour                                                                 |
| -------- | ----------------------------- | ------------------------------------------------------------------------- |
| RID      | `basic_rid_handler`           | Ignore external events claiming to alter _self_; allow `FORGET` if cached |
| Manifest | `basic_manifest_handler`      | De‑dup identical hash or older timestamp; label `NEW/UPDATE`              |
| Bundle   | `edge_negotiation_handler`    | Auto‑approve/propose edges, fallback to `FORGET` on invalid request       |
| Network  | `basic_network_output_filter` | Route events only to subscribers + affected peers                         |

---

## 8. Networking Layer

### Event Queues (`NetworkInterface`)

- **poll_event_queue** – outbound → neighbours that _poll_.
- **webhook_event_queue** – outbound → neighbours that accept webhooks.

> Flush → `request_handler.broadcast_events(...)` (webhook) or returned via `/events/poll`.

### Request/Response Handlers

All five protocol calls are thin wrappers around `httpx.post`, typed with pydantic models:

```python
payload = node.network.request_handler.fetch_bundles(node_rid, rids=[some_rid])
```

---

## 9. Protocol Endpoints (FastAPI‑style)

| Path                | Method | Purpose                      | Model                               |
| ------------------- | ------ | ---------------------------- | ----------------------------------- |
| `/events/broadcast` | POST   | Push events to **full** node | `EventsPayload`                     |
| `/events/poll`      | POST   | Pull events from node        | `PollEvents → EventsPayload`        |
| `/bundles/fetch`    | POST   | Bulk bundles                 | `FetchBundles → BundlesPayload`     |
| `/manifests/fetch`  | POST   | Bulk manifests               | `FetchManifests → ManifestsPayload` |
| `/rids/fetch`       | POST   | List cached RIDs             | `FetchRids → RidsPayload`           |

OpenAPI spec (`koi-net-protocol-openapi.json`) is auto‑generated from `basic_coordinator_node.py`.

---

## 10. Example Scripts

- **`examples/basic_coordinator_node.py`** (full node + custom handshake handler)
  – Rich‑logged FastAPI server on :8000; auto‑approves webhook edges.
- **`examples/basic_partial_node.py`** – minimal polling node.
- **`examples/full_node_template.py` / `partial_node_template.py`** – copy‑paste boilerplates.

---

## 11. Extending KOI‑net

1. **Custom RID types** – add in `rid-lib`; advertise via `NodeProfile.provides`.
2. **New pipeline logic** – register additional handlers or disable defaults by supplying your own `handlers=[...]` list to `NodeInterface`.
3. **Alternate transport** – swap out `RequestHandler.make_request` to use another client (e.g. `aiohttp`).
4. **Edge strategies** – override `edge_negotiation_handler` to implement trust/rate‑limit logic.

---

## 12. Development & Release

```bash
# clone & dev install
git clone https://github.com/BlockScience/koi-net
cd koi-net && python -m venv venv && source venv/bin/activate
pip install -e .[dev]

# run tests (none yet) / generate docs
python -m build            # wheel + sdist
# tags vX.Y.Z trigger GitHub Action → PyPI publish + Sigstore signing
```

---

## 13. Key Classes Quick‑Ref

| Class                | File                            | Core Methods & Properties                                                       |
| -------------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| `NodeInterface`      | `core.py`                       | `start()`, `stop()`, `.cache`, `.network`, `.processor`                         |
| `NetworkInterface`   | `network/interface.py`          | `push_event_to`, `poll_neighbors`, `fetch_remote_bundle`, `flush_webhook_queue` |
| `ProcessorInterface` | `processor/interface.py`        | `handle`, `flush_kobj_queue`, `register_handler`, `call_handler_chain`          |
| `KnowledgeObject`    | `processor/knowledge_object.py` | `.from_*` ctors, `.bundle`, `.normalized_event`                                 |
| `KnowledgeHandler`   | `processor/handler.py`          | `.create(...)` decorator constants `STOP_CHAIN`                                 |
| `EdgeProfile`        | `protocol/edge.py`              | `source`, `target`, `edge_type`, `status`, `rid_types`                          |

---

## 14. Glossary

- **RID** – Reference Identifier (strongly‑typed URI from `rid-lib`).
- **Bundle** – Manifest + optional contents (cached state).
- **Event** – FUN message (`NEW`, `UPDATE`, `FORGET`) carrying RID context.
- **Full node** – Runs API, receives webhooks, serves state.
- **Partial node** – Client‑only; polls peers but cannot serve state.
- **Edge negotiation** – Two‑step proposal (`PROPOSED` ➝ `APPROVED`) creating directional relation & broadcast method (WEBHOOK/POLL).
