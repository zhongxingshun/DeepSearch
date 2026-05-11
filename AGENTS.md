# DeepSearch Agent Memory

## Production Deployment Facts

- Production server: `192.168.10.65`
- SSH user: `akuvox`
- Project directory on server: `/home/akuvox/DeepSearch`
- Public URL: `http://192.168.10.65:3200`
- Frontend host port: `3200`
- Backend API port is internal behind frontend Nginx; use `http://127.0.0.1:3200/api/v1/health` for production health checks.

## Current Deployment Reality

As of 2026-05-11, the server project directory is not a Git repository and production does not pull application images from a registry.

Current production update flow:

1. Sync local code to `/home/akuvox/DeepSearch` with `rsync`.
2. Exclude production data and config:
   - `.env`
   - `backups`
   - `data/files`
   - `logs`
   - `node_modules`
   - `backend/.venv`
   - `frontend/dist`
3. SSH into the server.
4. Run `bash scripts/deploy.sh update`.

`deploy.sh update` currently builds application images on the server because `docker-compose.yml` uses `build:` for frontend/backend services and the script runs `docker compose build`.

## Target Deployment Direction

The desired future state is image-based deployment:

1. GitHub Actions builds frontend/backend images.
2. Images are tagged with the app version, for example `20260509.01`.
3. Images are pushed to a registry.
4. The server only runs `docker compose pull`, database migrations, and `docker compose up -d --no-build`.
5. `backend`, `celery-worker`, and `celery-beat` should use the same backend image with different commands.

Do not claim this target flow is already implemented until the compose file, deploy script, and CI workflow have actually been changed.

## Data Safety Rules

- Production data must not be lost.
- Never run `bash scripts/deploy.sh clean` on production unless the user explicitly asks for destructive cleanup and acknowledges data loss.
- Never run `docker compose down -v` on production.
- Do not overwrite the server `.env`; edit individual keys only when necessary.
- Before risky production updates, make database and `.env` backups. Use file-volume backup too when file storage behavior is involved.

Known backup location:

```bash
/home/akuvox/DeepSearch/backups
```

## Health And Version Checks

Use these checks after deployment:

```bash
bash scripts/deploy.sh health
curl -s http://127.0.0.1:3200/api/v1/health
```

The expected app version for the May 2026 release is `20260509.01`.

## Embedding In Third-Party Navigation Systems

DeepSearch can be embedded in a third-party navigation system iframe only when the frontend Nginx response allows that navigation system origin.

The frontend no longer sends `X-Frame-Options`; it uses CSP `frame-ancestors`.

Set the production server `.env` key:

```bash
FRAME_ANCESTORS="'self' http://192.168.254.99:8080"
```

Use the embedder origin, not the DeepSearch origin. Include protocol and port exactly. After changing it, rebuild/recreate the frontend container and verify:

```bash
curl -I http://127.0.0.1:3200/ | grep -i -E 'x-frame-options|content-security-policy'
```

Expected: no `X-Frame-Options`, and `Content-Security-Policy` contains the allowed navigation origin.
