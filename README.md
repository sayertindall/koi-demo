# koi-demo

## Quick start

1. **Clone repository**

   ```bash
   git clone https://github.com/sayertindall/koi-demo.git koi-demo
   cd koi-demo
   ```

2. **Create and activate virtual environment**

   ```bash
   make setup
   source .venv/bin/activate
   ```

3. **Install packages**

   ```bash
   make install
   ```

4. **Configure environment**

   ```bash
   cp config/docker/global.env.example config/docker/global.env
   ```

   Edit `config/docker/global.env` and set your:

   - `HACKMD_TOKEN`
   - `GITHUB_TOKEN`
   - `GITHUB_SECRET`

5. **Start services**

   ```bash
   make up
   ```

6. **Verify running containers**

   ```bash
   docker ps
   ```

   - Coordinator → port 8080
   - GitHub sensor → port 8001
   - HackMD sensor → port 8002
