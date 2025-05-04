# Plan: Scaffold and Implement Processor Nodes

This plan outlines the steps to create and implement Processor A (Repo Indexer) and Processor B (Note Indexer) within the existing `nodes/` directory structure, integrating them into the overall system defined by the PRD and `Processor.md`.

## Phase 1: Scaffolding Processor Nodes

**Goal:** Create the basic directory structure and file templates for both Processor A and Processor B nodes.

1.  **Task: Create Processor A Directory Structure**

    - **Action:** Create the directory `nodes/koi-net-processor-a-node/processor_a_node/`.
    - **Verification:** The directory structure exists.

2.  **Task: Create Processor A Basic Files**

    - **Action:** Inside `nodes/koi-net-processor-a-node/`, create the following empty files:
      - `processor_a_node/__init__.py`
      - `processor_a_node/__main__.py`
      - `processor_a_node/config.py`
      - `processor_a_node/core.py`
      - `processor_a_node/handlers.py`
      - `processor_a_node/server.py`
      - `Dockerfile`
      - `pyproject.toml`
      - `.gitignore`
      - `README.md` (optional)
    - **Verification:** All specified files exist in the correct locations.

3.  **Task: Populate Processor A Basic Files**

    - **Action:** Copy and adapt boilerplate code from an existing node (e.g., `koi-net-github-sensor-node`) into the newly created files for Processor A. Focus on:
      - `__init__.py`: Basic logging setup.
      - `config.py`: Structure for loading YAML/ENV, defining context-aware paths (adapt from sensor/coordinator config loaders).
      - `core.py`: Placeholder `NodeInterface` initialization (adapt profile from `Processor.md`).
      - `server.py`: Basic FastAPI app setup with lifespan manager and health check, placeholder KOI endpoints.
      - `Dockerfile`: Adapt from sensor Dockerfile (adjust port, entrypoint).
      - `pyproject.toml`: Basic build system setup and core dependencies (fastapi, uvicorn, koi-net, rid-lib, etc.).
      - `.gitignore`: Copy from sensor node.
    - **Verification:** Files contain basic, runnable (though not functional) structures.

4.  **Task: Create Processor B Directory Structure**

    - **Action:** Create the directory `nodes/koi-net-processor-b-node/processor_b_node/`.
    - **Verification:** The directory structure exists.

5.  **Task: Create Processor B Basic Files**

    - **Action:** Inside `nodes/koi-net-processor-b-node/`, create the same set of basic files as listed in Task 1.2 (adjusting `processor_a_node` to `processor_b_node`).
    - **Verification:** All specified files exist.

6.  **Task: Populate Processor B Basic Files**
    - **Action:** Similar to Task 1.3, adapt boilerplate code from an existing node or the newly scaffolded Processor A into Processor B's files. Adjust port numbers, node names, and `NodeInterface` profile according to `Processor.md`.
    - **Verification:** Files contain basic, runnable structures.

## Phase 2: Implementing Processor A (Repo Indexer)

**Goal:** Implement the full functionality of Processor A based on `Processor.md`.

1.  **Task: Implement Processor A Config Loading (`config.py`)**

    - **Action:** Fully implement the configuration loading logic, defining necessary keys (runtime, edges, processor-specific settings) and ensuring correct path/URL resolution based on local/Docker context.
    - **Verification:** Configuration values (BASE_URL, COORDINATOR_URL, CACHE_DIR, etc.) are correctly loaded and logged on startup.

2.  **Task: Implement Processor A Core (`core.py`)**

    - **Action:** Correctly initialize `NodeInterface` with the specific profile defined in `Processor.md` (consuming `GithubCommit`, providing no new RIDs).
    - **Verification:** `NodeInterface` initializes without errors, using correct config values.

3.  **Task: Implement Processor A Handlers (`handlers.py`)**

    - **Action:** Implement the event handlers:
      - `Network` handler for discovering Coordinator and GitHub Sensor, proposing edges.
      - `Manifest` handler for receiving `GithubCommit` manifests and triggering bundle fetching.
      - `Bundle` handler for processing `GithubCommit` bundles, extracting data, and updating the internal search index. Define and implement the structure for `search_index`.
    - **Verification:** Handlers are registered and log messages indicate correct processing steps when events are simulated or received.

4.  **Task: Implement Processor A Server (`server.py`)**

    - **Action:** Implement the FastAPI application:
      - Ensure all standard KOI endpoints (`/koi-net/...`) are correctly routed to `node.network.response_handler` or `node.processor`.
      - Implement the custom `/search` endpoint logic to query the internal `search_index` based on the 'q' parameter and return JSON results.
    - **Verification:** The server runs, KOI endpoints respond correctly (tested via `curl` or `httpx`), and the `/search` endpoint returns expected results based on indexed data.

5.  **Task: Finalize Processor A Dockerfile & Dependencies**
    - **Action:** Ensure the `Dockerfile` correctly builds the Processor A node, installs all necessary dependencies, exposes the correct port (e.g., 8011), and sets the appropriate entrypoint/command. Update `pyproject.toml` if any additional libraries were needed (e.g., specific indexing libraries).
    - **Verification:** `docker build` succeeds for Processor A.

## Phase 3: Implementing Processor B (Note Indexer)

**Goal:** Implement the full functionality of Processor B based on `Processor.md`.

1.  **Task: Implement Processor B Config Loading (`config.py`)**

    - **Action:** Implement configuration loading similar to Processor A, adapting for Processor B's specific settings.
    - **Verification:** Configuration values are correctly loaded.

2.  **Task: Implement Processor B Core (`core.py`)**

    - **Action:** Initialize `NodeInterface` with the profile from `Processor.md` (consuming `HackMDNote`, providing no new RIDs).
    - **Verification:** `NodeInterface` initializes correctly.

3.  **Task: Implement Processor B Handlers (`handlers.py`)**

    - **Action:** Implement event handlers:
      - `Network` handler (Coordinator, HackMD Sensor discovery).
      - `Manifest` handler for `HackMDNote` (triggering bundle fetch).
      - `Bundle` handler for `HackMDNote` (processing note content, updating internal index). Define `search_index`. Consider adding a markdown parsing library if needed.
    - **Verification:** Handlers log correct processing steps. Index is updated.

4.  **Task: Implement Processor B Server (`server.py`)**

    - **Action:** Implement the FastAPI application, KOI endpoints, and the custom `/search` endpoint logic for querying the note index.
    - **Verification:** Server runs, endpoints respond correctly, `/search` returns expected results.

5.  **Task: Finalize Processor B Dockerfile & Dependencies**
    - **Action:** Ensure `Dockerfile` builds, installs dependencies (including any parsing libs), exposes the correct port (e.g., 8012), and has the right entrypoint. Update `pyproject.toml`.
    - **Verification:** `docker build` succeeds for Processor B.

## Phase 4: Integration and Configuration

**Goal:** Integrate the new Processor nodes into the overall system configuration and Docker Compose setup.

1.  **Task: Create Processor Configuration Files**

    - **Action:** Create `processor-a.yaml` and `processor-b.yaml` within both `config/docker/` and `config/local/` directories. Populate them with the necessary runtime, edges, and processor-specific configurations identified in `Processor.md` and the implementation phase, adjusting URLs/paths for docker vs. local context.
    - **Verification:** Config files exist and contain valid YAML structures.

2.  **Task: Update Docker Compose (`docker-compose.yaml`)**

    - **Action:** Add new service definitions for `processor-a` and `processor-b`. Ensure:
      - Correct `build.context`.
      - Mapping of ports (e.g., 8011:8011, 8012:8012).
      - Mounting of `/config` volume (read-only).
      - Mounting of shared `cache_data` volume (`/data/cache`).
      - Mounting of persistent state volumes (e.g., `processor_a_state:/app/.koi/processor-a`, `processor_b_state:/app/.koi/processor-b`).
      - Setting `RUN_CONTEXT=docker` and `KOI_CONFIG_MODE=docker` environment variables.
      - Loading `config/docker/global.env`.
      - Correct `depends_on` clauses (e.g., depend on coordinator, potentially sensors).
      - Appropriate `healthcheck` definitions targeting their `/health` endpoints.
      - Adding them to the `koinet` network.
    - **Verification:** `docker compose up --build` starts all services (including processors) without errors. Health checks pass.

3.  **Task: Test Complete System**
    - **Action:** Run the full system using `docker compose up`. Verify:
      - All nodes start and register with the Coordinator (check Coordinator logs).
      - Sensors connect to Processors (check logs).
      - Processors receive manifests from Sensors (check logs).
      - Processors successfully index data.
      - Processor `/search` endpoints can be queried (`curl http://localhost:8011/search?q=...`) and return expected results.
    - **Verification:** End-to-end data flow (Sensor -> Processor -> Index -> Search API) functions as expected according to the PRD's simplified scope.
