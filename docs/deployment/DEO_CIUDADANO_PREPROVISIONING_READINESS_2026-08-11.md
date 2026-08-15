# DEO Ciudadano Pre-Provisioning Readiness

Release deployment is artifact-based: release ID, SHA-256, extraction into
`/opt/datosenorden/releases/<RELEASE_ID>`, and explicit activation through the
`current` symlink. The pack has no VPS address, credential, provider token, or
workstation drive assumption.

## Prepared checks

- `host_preflight_ubuntu.sh`: read-only host capacity and service inventory.
- `configure_ufw.sh`: requires a confirmed active SSH session before enabling
  UFW; only SSH, HTTP, and HTTPS are allowed.
- `configure_postgres_beta.sh`: reads a mode-0600 local password file and
  deletes it after creating the beta role/database.
- `deploy_release_ubuntu.sh --prepare`: validates SHA-256, rejects an existing
  release, prepares its venv, performs `pip check` and Reflex dry compile, then
  writes the readiness marker and removes runtime-user write permissions.
- `activate_release_ubuntu.sh`: accepts only a complete prepared release,
  atomically changes `current`, restarts and smokes the service, and restores
  the old `current` on failure without touching database state.
- `post_deploy_smoke.sh`: validates systemd, loopback, private ports, symlink,
  available memory, and disk.

## Day-of gates

1. Verify target fingerprint and run host preflight.
2. Bootstrap packages, user, filesystem layout, and local PostgreSQL.
3. Prepare external beta configuration and install artifact.
4. Validate systemd and Caddy locally; run technical smoke.
5. Stop before DNS. `beta.datosenorden.cl`, TLS, WebSocket exterior QA, backup
   offsite transfer, and restore rehearsal remain later gates.

Failure labels: `SOURCE_FIX_REQUIRED`, `TARGET_REMEDIATION_REQUIRED`,
`CONFIGURATION_REQUIRED`, `SECURITY_NO_GO`, and `ARTIFACT_INTEGRITY_FAILURE`.
