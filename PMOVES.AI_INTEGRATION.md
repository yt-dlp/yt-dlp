# PMOVES.AI Integration Guide for PMOVES YT

## Overview

PMOVES.YT is integrated with PMOVES.AI production infrastructure.

**For comprehensive PMOVES.AI integration documentation, see the [Universal Submodule Integration Guide](../../pmoves/docs/PMOVES.AI_SUBMODULE_INTEGRATION_GUIDE.md).** This guide covers:
- CHIT secret management (v1 vs v2 manifest formats)
- Bootstrap process and mode detection
- Secrets categorization (environment vs repository)
- Tier classification and configuration
- Quick start for new submodules

## Integration Complete

The PMOVES.AI integration template has been applied to PMOVES YT.

### Recent Fixes (2026-02-08)

PMOVES.AI received critical credential management fixes (commits `1894a284`, `f943db5b`):
- ✅ Fixed broken bash regex for environment variable counting
- ✅ Fixed security issue: tier fallback now fails explicitly instead of silently loading all tiers
- ✅ Fixed version alignment: bootstrap now reports v5
- ✅ Fixed credential wizard GitHub Actions secret format

**See:** [Submodule Sync Guide](https://github.com/POWERFULMOVES/PMOVES.AI/blob/main/pmoves/docs/SUBMODULE_CREDENTIAL_FIX_SYNC_GUIDE.md)

## Credential Management

PMOVES.YT inherits credentials from parent PMOVES.AI using the CHIT (Compressed Hierarchical Information Transfer) system.

### Bootstrap Credential Loading

```bash
# From PMOVES.YT directory (when PMOVES.YT is a submodule)
cd /path/to/PMOVES.AI/pmoves/PMOVES-YT
source ../../scripts/bootstrap_credentials.sh

# OR if PMOVES.YT is a sibling repo
cd /path/to/PMOVES-YT
source ../PMOVES.AI/pmoves/scripts/bootstrap_credentials.sh
```

The bootstrap automatically:
1. Detects docked vs standalone mode
2. Loads CHIT Geometry Packet (`env.cgp.json`) if available
3. Falls back to git-crypt, Docker Secrets, or parent credentials
4. Generates tier-specific environment files (`.env.bootstrap`)

### CHIT Search Locations

The bootstrap searches for `env.cgp.json` in:
1. `./data/chit/env.cgp.json` - Current directory
2. `./pmoves/data/chit/env.cgp.json` - Current repo's pmoves directory
3. `../pmoves/data/chit/env.cgp.json` - Parent's pmoves directory
4. `../../pmoves/data/chit/env.cgp.json` - Grandparent's pmoves directory
5. `../../../pmoves/data/chit/env.cgp.json` - Great-grandparent's pmoves directory

**Note:** The bootstrap script is at `scripts/bootstrap_credentials.sh` at the PMOVES.AI root, not `pmoves/scripts/bootstrap_credentials.sh`.

### Mode Detection

- **DOCKED MODE**: Running inside PMOVES.AI Docker stack → loads from parent only
- **STANDALONE MODE**: Independent operation → tries CHIT → git-crypt → Docker → parent

See `pmoves/docs/SECRETS.md` in parent PMOVES.AI for full documentation.

## Environment Files

This integration provides environment files for both shell sourcing and Docker Compose:

### Shell Usage (for development/testing)
Source the `.sh` versions directly in your shell:
```bash
source env.shared.sh
source env.tier-worker.sh
```

### Docker Compose Usage
Use the non-`.sh` versions with `env_file` directive:
```yaml
services:
  pmoves-yt:
    env_file:
      - env.shared
```

## Next Steps

### 1. Customize Environment Variables

Edit the following files with your service-specific values:

- `env.shared` / `env.shared.sh` - Base environment configuration
- `env.tier-worker` / `env.tier-worker.sh` - Tier-specific environment

Note: Both formats are provided for flexibility. The `.sh` files use `export` for shell sourcing, while non-`.sh` files use plain `KEY=value` for Docker Compose.

**Important:**
- `env.shared` is a **template file** for environment configuration structure
- **DO NOT** store actual secret values in `env.shared` for submodules
- Credentials are inherited from parent PMOVES.AI via `bootstrap_credentials.sh`
- The template uses empty defaults (`${VAR:-}`) to fail fast if credentials are missing
- In parent PMOVES.AI, `env.shared` contains actual values that get CHIT-encoded

### 2. Update Docker Compose

Add the PMOVES.AI environment anchor to your `docker-compose.yml`:

```yaml
services:
  pmoves-yt:
    <<: [*env-tier-worker, *pmoves-healthcheck, *pmoves-labels]
    image: ghcr.io/powerfulmoves/pmoves-yt:latest
    ports:
      - "8077:8077"
    environment:
      SERVICE_NAME: pmoves-yt
      SERVICE_PORT: 8077
      METRICS_PORT: 9180
```

**Important:** Use the array merge form `<<: [*anchor1, *anchor2, ...]` not separate `<<:` directives. This preserves list merges and is more reliable.

**Note on healthcheck ports:** The `${SERVICE_PORT:-8080}` in the healthcheck template is interpolated from the host environment (or `.env` file), not from the service's `environment` block. To override the port, either:
- Set `SERVICE_PORT` in your host environment or `.env` file before running `docker compose`
- Or override `healthcheck.test` explicitly in each service with the concrete URL

### 3. Integrate Health Check

Add the health check endpoint to your service:

```python
from pmoves_health import add_custom_check, get_health_status

@app.get("/healthz")
async def health_check():
    return await get_health_status()
```

### 4. Add Service Announcement

Add NATS service announcement to your startup using the lifespan pattern:

```python
from contextlib import asynccontextmanager
from pmoves_announcer import announce_service

@asynccontextmanager
async def lifespan(app):
    # Startup
    await announce_service(
        slug="pmoves-yt",
        name="PMOVES YT",
        url="http://pmoves-yt:8077",
        port=8077,
        tier="worker"
    )
    yield
    # Shutdown (if needed)

app = FastAPI(lifespan=lifespan)
```

Note: The `@app.on_event("startup")` decorator is deprecated in FastAPI. Use the `lifespan` context manager instead.

### 5. Test Integration

```bash
# Test health check
curl http://localhost:8077/healthz

# Verify environment variables loaded
docker compose exec pmoves-yt env | grep PMOVES

# Verify NATS announcement
nats sub "services.announce.v1"
```

## Service Details

- **Name:** PMOVES YT
- **Slug:** pmoves-yt
- **Tier:** worker
- **Port:** 8077
- **Health Check:** http://localhost:8077/healthz
- **Metrics:** http://localhost:9180/metrics
- **NATS Enabled:** True
- **GPU Enabled:** False

## Files Created

- `env.shared` / `env.shared.sh` - Base PMOVES.AI environment
- `env.tier-worker` / `env.tier-worker.sh` - Tier-specific environment
- `pmoves_health/` - Health check module
- `pmoves_announcer/` - NATS service announcer
- `pmoves_registry/` - Service registry client
- `docker-compose.pmoves.yml` - PMOVES.AI YAML anchors

Note: CHIT secrets management is handled by parent PMOVES.AI. Submodules do not need their own `secrets_manifest_v2.yaml` - credentials are inherited via the bootstrap script.

## Docker Compose Notes

1. **YAML Merge Syntax**: Use `<<: [*anchor1, *anchor2]` for multiple anchors. Do not use separate `<<:` directives as this violates YAML spec.

2. **Environment Format**: Use mapping syntax (`KEY: value`) not array syntax (`- KEY=value`) for better readability.

3. **Health Check Ports**: The `${SERVICE_PORT:-8080}` in healthcheck is interpolated from the host environment or `.env` file, NOT from the service's `environment` block. Set it in your `.env` file before running docker compose, or override `healthcheck.test` explicitly per service.

4. **Prometheus Labels**: Labels use slash separator (`prometheus.io/port`) not dot (`prometheus.io.port`).

## Support

For questions or issues, see the PMOVES.AI documentation.
