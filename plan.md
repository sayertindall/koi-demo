1. **Decide on your Fly.io app names**

   - For each service choose a unique name, e.g.:

     - `koi-demo-coordinator`
     - `koi-demo-github-sensor`
     - `koi-demo-hackmd-sensor`
     - `koi-demo-processor-a`
     - `koi-demo-processor-b`

2. **Create Fly volumes** (once per service)

   ```bash
   flyctl volumes create coordinator_state_data  --region <region> --size 1
   flyctl volumes create github_sensor_state_data --region <region> --size 1
   flyctl volumes create hackmd_sensor_state_data  --region <region> --size 1
   flyctl volumes create processor_a_state_data    --region <region> --size 1
   flyctl volumes create processor_b_state_data    --region <region> --size 1
   ```

3. **Modify each service’s Dockerfile**
   At top of `nodes/koi-net-<service>-node/Dockerfile`, insert:

   ```dockerfile
   ARG SERVICE_NAME
   WORKDIR /app
   COPY . .
   COPY ../../config/docker/global.env /config/global.env
   COPY ../../config/docker/${SERVICE_NAME}.yaml /config/config.yaml
   ```

   - Builds will use `SERVICE_NAME` to pick the right YAML.

4. **Create `fly.toml` in each service folder**
   For example, in `nodes/koi-net-coordinator-node/fly.toml`:

   ```toml
   app = "your-org-coordinator"
   kill_signal = "SIGINT"
   kill_timeout = 5

   [build]
     dockerfile = "Dockerfile"
     buildargs = { SERVICE_NAME = "coordinator" }

   [env]
     RUN_CONTEXT     = "docker"
     KOI_CONFIG_MODE = "docker"
     RID_CACHE_DIR   = "/data/cache"

   [[mounts]]
     source      = "coordinator_state_data"
     destination = "/app/.koi/coordinator"

   [[services]]
     internal_port = 8080
     protocol      = "tcp"
     [[services.ports]]
       handlers = ["http"]
       port     = 80
   ```

   - Repeat for each service, adjusting `app`, `buildargs.SERVICE_NAME`, volume name, `internal_port`.

5. **Update service-to-service endpoints**
   In code or config, replace Docker-Compose hostnames with Fly DNS:

   ```
   your-org-coordinator.internal:8080
   your-org-github-sensor.internal:8001
   …
   ```

6. **Commit all config changes**

   ```bash
   git add config/docker/*.yaml \
           nodes/*/Dockerfile \
           nodes/*/fly.toml
   git commit -m "Add Fly.toml and config integration"
   ```

7. **Push to GitHub**

   ```bash
   git push origin main
   ```

8. **Create `FLY_API_TOKEN` secret**

   - Run locally:

     ```bash
     flyctl auth token
     ```

   - In GitHub repo → Settings → Secrets → Actions → New repository secret:

     - **Name**: `FLY_API_TOKEN`
     - **Value**: the token from above

9. **Add path-filter workflow**
   Create `.github/workflows/deploy.yml` with:

   ```yaml
   name: CI/CD → Fly.io

   on:
     push:
       branches: [main]

   jobs:
     filter:
       runs-on: ubuntu-latest
       outputs:
         coordinator: ${{ steps.paths.outputs.coordinator }}
         github_sensor: ${{ steps.paths.outputs.github_sensor }}
         hackmd_sensor: ${{ steps.paths.outputs.hackmd_sensor }}
         processor_a: ${{ steps.paths.outputs.processor_a }}
         processor_b: ${{ steps.paths.outputs.processor_b }}

       steps:
         - uses: actions/checkout@v3
         - id: paths
           uses: dorny/paths-filter@v2
           with:
             filters:
               coordinator:
                 - "nodes/koi-net-coordinator-node/**"
                 - "config/docker/coordinator.yaml"
               github_sensor:
                 - "nodes/koi-net-github-sensor-node/**"
                 - "config/docker/github-sensor.yaml"
               hackmd_sensor:
                 - "nodes/koi-net-hackmd-sensor-node/**"
                 - "config/docker/hackmd-sensor.yaml"
               processor_a:
                 - "nodes/koi-net-processor-a-node/**"
                 - "config/docker/processor-a.yaml"
               processor_b:
                 - "nodes/koi-net-processor-b-node/**"
                 - "config/docker/processor-b.yaml"

     deploy:
       needs: filter
       runs-on: ubuntu-latest
       strategy:
         matrix:
           service:
             [
               coordinator,
               github_sensor,
               hackmd_sensor,
               processor_a,
               processor_b,
             ]
       if: needs.filter.outputs[matrix.service] == 'true'
       steps:
         - uses: actions/checkout@v3
         - uses: superfly/flyctl-actions/setup-flyctl@master
         - name: Deploy ${{ matrix.service }}
           working-directory: nodes/koi-net-${{ matrix.service }}-node
           env:
             FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
           run: flyctl deploy --remote-only
   ```

10. **Commit and push workflow**

    ```bash
    git add .github/workflows/deploy.yml
    git commit -m "Add Fly.io CI/CD workflow"
    git push origin main
    ```

11. **Trigger first deploy**

    - Push any change to `main` (e.g. a comment)
    - Watch Actions → deploy job logs for each changed service.

12. **Verify services**

    ```bash
    flyctl status --app your-org-coordinator
    flyctl logs --app your-org-coordinator
    ```

    - Repeat for each app.

13. **Test inter-service calls**

    - Confirm sensors reach coordinator at `<coordinator>.internal:8080`
    - Confirm processors reach sensors similarly.

14. **Monitor & scale**

    - Use `flyctl scale memory`, `flyctl scale vm` as needed:

      ```bash
      flyctl scale vm shared-cpu-1x --app your-org-coordinator
      ```

15. **Clean up old Docker Compose**

    - You can now retire `docker-compose.yaml` or keep it for local development.

16. **Document your setup**

    - Update `README.md` with Fly.io instructions, how to run locally vs. on Fly, and CI/CD notes.

---

Following these 20 steps gives you a fully-automated, monorepo-friendly Fly.io deployment with shared configuration and on-push CI/CD.
