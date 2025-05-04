.PHONY: setup install clean coordinator github hackmd demo-coordinator demo-github demo-hackmd docker-clean rebuild docker-rebuild clean-cache up down

setup:
	@echo "Creating virtual environment with uv..."
	uv venv --python 3.12
	@echo "Virtual environment created at .venv"
	@echo "Run: source .venv/bin/activate"

install:
	@echo "Installing root package..."
	uv pip install -e .
	@echo "Installing coordinator service..."
	uv pip install -e nodes/koi-net-coordinator-node/
	@echo "Installing github service..."
	uv pip install -e nodes/koi-net-github-sensor-node/
	@echo "Installing hackmd service..."
	uv pip install -e nodes/koi-net-hackmd-sensor-node/
	@echo "All packages installed successfully!"

clean:
	@echo "Removing virtual environment..."
	rm -rf .venv
	@echo "Removing build artifacts..."
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	@echo "Clean complete."

clean-cache:
	@echo "Removing cache..."
	rm -rf .koi
	@echo "Cache removed."

coordinator:
	@echo "Running Coordinator Node..."
	export KOI_CONFIG_MODE=local
	.venv/bin/python3 -m nodes.koi-net-coordinator-node.coordinator_node

github:
	@echo "Running Github Node..."
	export KOI_CONFIG_MODE=local
	.venv/bin/python3 -m nodes.koi-net-github-sensor-node.github_sensor_node

hackmd:
	@echo "Running HackMD Node..."
	export KOI_CONFIG_MODE=local
	.venv/bin/python3 -m nodes.koi-net-hackmd-sensor-node.hackmd_sensor_node

demo-coordinator:
	@echo "Starting Coordinator via Docker Compose..."
	docker compose build --no-cache coordinator
	docker compose up coordinator

demo-github:
	@echo "Starting GitHub sensor via Docker Compose..."
	docker compose build --no-cache github-sensor
	docker compose up -d github-sensor

demo-hackmd:
	@echo "Starting HackMD sensor via Docker Compose..."
	docker compose build --no-cache hackmd-sensor
	docker compose up -d hackmd-sensor

docker-clean:
	@echo "Cleaning up all Docker containers and images..."
	docker compose down --rmi all
	@echo "Docker cleanup complete."

docker-rebuild:
	@echo "Rebuilding Docker images with no cache..."
	docker compose build --no-cache
	@echo "Starting Docker services..."
	docker compose up -d

up:
	@echo "Starting Docker services..."
	docker compose up -d

down:
	@echo "Stopping Docker services..."
	docker compose down