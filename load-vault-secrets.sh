#!/usr/bin/env bash
#
# load-vault-secrets.sh — Authenticate to Vault via AppRole, fetch OpenOSINT
# secrets, export them as environment variables, then exec the wrapped command.
#
# Usage: load-vault-secrets.sh <command> [args...]
#
# Exits non-zero if Vault authentication fails or a CRITICAL secret is missing.
# Optional secrets that are not yet stored in Vault produce a warning and the
# script continues without them.

set -euo pipefail

VAULT_BIN="/usr/bin/vault"
VAULT_HOST="tuvjaxonp03"
VAULT_BASE="secret/hosts/${VAULT_HOST}"

# ---------------------------------------------------------------------------
# Vault authentication (AppRole)
# ---------------------------------------------------------------------------
if [ ! -r /etc/vault/vault_addr ]; then
    echo "ERROR: cannot read /etc/vault/vault_addr" >&2
    exit 1
fi
if [ ! -r /etc/vault/host/role_id ] || [ ! -r /etc/vault/host/secret_id ]; then
    echo "ERROR: cannot read AppRole credentials in /etc/vault/host/" >&2
    exit 1
fi

VAULT_ADDR="$(cat /etc/vault/vault_addr)"
export VAULT_ADDR

# Authenticate; capture token. Fail hard on auth failure.
if ! VAULT_TOKEN="$("${VAULT_BIN}" write -field=token auth/approle/login \
        role_id="$(cat /etc/vault/host/role_id)" \
        secret_id="$(cat /etc/vault/host/secret_id)")"; then
    echo "ERROR: Vault AppRole authentication failed" >&2
    exit 1
fi
export VAULT_TOKEN

# ---------------------------------------------------------------------------
# Helper: fetch a single-field secret from Vault KV v2.
#   $1 = full vault path (e.g. secret/hosts/tuvjaxonp03/openosint/shodan_api_key)
#   stdout = value (empty if missing/404)
#   returns 0 if found, 1 if missing/empty
# ---------------------------------------------------------------------------
fetch_secret() {
    local path="$1"
    local value
    value="$("${VAULT_BIN}" kv get -field=value "${path}" 2>/dev/null || true)"
    if [ -n "${value}" ]; then
        printf '%s' "${value}"
        return 0
    fi
    return 1
}

# ---------------------------------------------------------------------------
# Helper: load an optional secret (warn on missing, continue).
#   $1 = env var name
#   $2 = vault sub-path (relative to VAULT_BASE)
# ---------------------------------------------------------------------------
load_optional() {
    local envvar="$1"
    local subpath="$2"
    local value
    if value="$(fetch_secret "${VAULT_BASE}/${subpath}")"; then
        export "${envvar}=${value}"
        echo "[vault] loaded ${envvar} from ${subpath}"
    else
        echo "[vault] WARNING: ${envvar} not found at ${subpath} (optional, continuing)" >&2
    fi
}

# ---------------------------------------------------------------------------
# Helper: load a critical secret (fail hard on missing).
#   $1 = env var name
#   $2 = vault sub-path
# ---------------------------------------------------------------------------
load_critical() {
    local envvar="$1"
    local subpath="$2"
    local value
    if value="$(fetch_secret "${VAULT_BASE}/${subpath}")"; then
        export "${envvar}=${value}"
        echo "[vault] loaded ${envvar} from ${subpath}"
    else
        echo "[vault] ERROR: ${envvar} not found at ${subpath} (CRITICAL — aborting)" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Helper: load an optional secret with a fallback path.
#   $1 = env var name
#   $2 = primary sub-path
#   $3 = fallback sub-path
# ---------------------------------------------------------------------------
load_optional_with_fallback() {
    local envvar="$1"
    local primary="$2"
    local fallback="$3"
    local value
    if value="$(fetch_secret "${VAULT_BASE}/${primary}")"; then
        export "${envvar}=${value}"
        echo "[vault] loaded ${envvar} from ${primary}"
    elif value="$(fetch_secret "${VAULT_BASE}/${fallback}")"; then
        export "${envvar}=${value}"
        echo "[vault] loaded ${envvar} from ${fallback} (fallback)"
    else
        echo "[vault] WARNING: ${envvar} not found at ${primary} or ${fallback} (optional, continuing)" >&2
    fi
}

# ---------------------------------------------------------------------------
# Fetch all secrets
# ---------------------------------------------------------------------------
load_optional              SHODAN_API_KEY       openosint/shodan_api_key
load_optional_with_fallback VIRUSTOTAL_API_KEY  openosint/virustotal_api_key   reputation-lookup/virustotal-api-key
load_optional_with_fallback ABUSEIPDB_API_KEY   openosint/abuseipdb_api_key    reputation-lookup/abuseipdb-api-key
load_optional              CENSYS_API_ID        openosint/censys_api_id
load_optional              CENSYS_SECRET        openosint/censys_secret
load_optional              GITHUB_TOKEN         openosint/github_token
load_optional              IPINFO_TOKEN         openosint/ipinfo_token
load_optional              IP2LOCATION_API_KEY  openosint/ip2location_api_key
load_critical              OPENAI_API_KEY       openosint/openai_api_key

# ---------------------------------------------------------------------------
# Exec the wrapped command
# ---------------------------------------------------------------------------
if [ "$#" -eq 0 ]; then
    echo "ERROR: no command specified to exec" >&2
    exit 1
fi

echo "[vault] exec: $*"
exec "$@"