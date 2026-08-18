# VPS Go-Live Steps

This runbook deploys an immutable public release to Ubuntu 24.04 LTS. It does
not deploy from a mutable clone, and it does not contain credentials.

## Preconditions

- The minimum supported target is a verified Ubuntu 24.04 VPS with 2 vCPU,
  about 4 GiB RAM, and at least 50 GB free storage. This profile is restricted
  to one low-traffic Reflex service with local PostgreSQL; build, migration,
  backup, and restore work must run sequentially, without beta/production
  service overlap.
- On later deployments to the minimum profile, stop the active application
  before target-side dependency installation and Reflex compilation. Restoring
  zero-downtime deployment requires the recommended profile or a separately
  certified prebuilt-runtime artifact contract; it must not be improvised.
- The recommended target remains 3 vCPU and about 8 GB RAM. Falling below the
  recommended CPU or memory is a capacity warning, not a blocking failure,
  when the minimum profile and its operational restrictions are satisfied.
- A minimum-memory target should have at least 1 GiB swap as an emergency
  buffer. Swap is not runtime capacity: sustained use is a scale-up trigger.
- SSH key access and the host fingerprint are verified out of band.
- The release artifact, its SHA-256, and its 40-hex release ID are known.
- A root-owned `/etc/datosenorden/beta.env` exists with mode `0640` and group
  `datosenorden`. Its public URLs are `https://beta.datosenorden.cl`; DNS is
  still a separate gate.

## Provisioning sequence

1. **GATE**: upload the certified artifact through an authenticated channel and
   verify it before executing anything from it:

   ```bash
   echo '<ARTIFACT_SHA256>  /secure-upload/datosenorden.tar' | sha256sum -c -
   ```

2. **GATE**: run the read-only preflight from the verified artifact. Stop on
   `FAIL`:

   ```bash
   tar -xOf /secure-upload/datosenorden.tar scripts/host_preflight_ubuntu.sh | sudo bash
   ```

3. **AUTOMATED**: bootstrap packages, the service user, and filesystem layout
   from the same verified artifact:

   ```bash
   tar -xOf /secure-upload/datosenorden.tar scripts/server_setup_ubuntu.sh | \
     sudo env INSTALL_LIBREOFFICE=0 bash
   ```

   Do not clone, pull, or retain a mutable Git worktree on the host.

4. **MANUAL/GATE**: from a verified SSH session run the firewall script from
   the verified artifact with `--confirmed-ssh`. Provider firewall:
   allow administrative SSH, TCP 80, TCP 443; deny public TCP 3000 and 5432.
5. **AUTOMATED**: prepare the immutable release exactly once from the same
   artifact. Preparation neither reads the production environment nor changes
   `current`, systemd, or the database:

   ```bash
   tar -xOf /secure-upload/datosenorden.tar scripts/deploy_release_ubuntu.sh | sudo bash -s -- \
     --prepare \
     --artifact /secure-upload/datosenorden.tar \
     --sha256 <ARTIFACT_SHA256> \
     --release-id <RELEASE_ID>
   ```

   It verifies the archive, extracts into a previously absent release
   directory, creates the venv, installs dependencies, performs `pip check`
   and Reflex dry compile, then writes `.deo-release-ready`. Only after all
   checks pass does it remove runtime-user/group write permissions. A second
   prepare for the same release is intentionally rejected.
6. **MANUAL/GATE**: create a mode-0600 password file outside the release, then
   execute `configure_postgres_beta.sh` from the verified artifact with the
   password-file path. PostgreSQL must remain loopback-only. Create the
   root-owned external `/etc/datosenorden/beta.env` only after the role and
   database exist; never write it inside the release.
7. **GATE**: use the prepared release tooling, with the external environment,
   to migrate from the certified Alembic revision and import the independently
   verified production data package. Reimport the same package and require
   zero inserts/count drift. `current` must still be absent on a first deploy
   or unchanged on an update, and the application service must remain stopped:

   ```bash
   release=/opt/datosenorden/releases/<RELEASE_ID>
   sudo -u datosenorden bash -c 'set -a; . "$1"; set +a; cd "$2"; exec .venv/bin/python -m alembic upgrade head' \
     -- /etc/datosenorden/beta.env "$release"
   sudo -u datosenorden bash -c 'env_file="$1"; release="$2"; shift 2; set -a; . "$env_file"; set +a; cd "$release"; exec .venv/bin/python scripts/import_production_data.py "$@"' \
     -- /etc/datosenorden/beta.env "$release" \
     --package /secure-upload/<DATA_PACKAGE>.zip \
     --sha256 <DATA_PACKAGE_SHA256> \
     --expected-database datosenorden_beta \
     --target-environment production \
     --code-release <RELEASE_ID> \
     --confirm-production <PACKAGE_ID>
   ```

8. **GATE**: execute the prepared release's prelaunch/deploy checks against the
   migrated database. This is the pre-activation application smoke; it must not
   expose traffic, change `current`, or write inside the release. PREPARE is the
   sole authority for Reflex compilation: it compiles before hardening and before
   `.deo-release-ready` is written. Post-PREPARE validation uses
   `scripts/prelaunch_public_check.py --read-only` (via `deploy_check.py`) and
   must never invoke Reflex compilation or import the Reflex application.
9. **GATE**: extract only `deployment/datosenorden.service` and
   `deployment/Caddyfile` from the verified artifact into their system
   locations, then validate and reload them. `deployment/Caddyfile` is
   Caddyfile syntax (not native JSON), so declare its adapter explicitly:
   `sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`.
   Validate the unit with `systemd-analyze verify
   /etc/systemd/system/datosenorden.service`, then reload the Caddyfile with
   `sudo caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.
   Enable the application unit without starting it: `sudo systemctl enable
   datosenorden`. Make Caddy ready according to its separately validated
   foundation before activation.
10. **AUTOMATED**: activate the already prepared release; never invoke prepare
    again for the same release:

    ```bash
    tar -xOf /secure-upload/datosenorden.tar scripts/activate_release_ubuntu.sh | sudo bash -s -- \
      --release-id <RELEASE_ID> \
      --confirm-ready <RELEASE_ID>
    ```

    The repeated release ID is an explicit operator assertion that environment,
    migration, data import and pre-activation checks passed. Activation also
    verifies the readiness marker, venv, smoke script, installed systemd unit,
    external environment and immutable permissions. It atomically switches `current`,
    restarts systemd and runs post-deploy smoke without pip, build, Alembic or
    data import. First activation leaves `previous` absent. On an update,
    successful activation sets `previous` to the old `current`.
11. **FAILURE CONTRACT**: if restart or post-activation smoke fails, activation
    stops the failed service and restores the old `current`. It then attempts
    to restart the old release; if that is unhealthy the service stays stopped.
    On a failed first activation, `current` is removed and `previous` remains
    absent. Database state is never rolled back by application activation.
12. **STOP**: do not create the DNS record, enable HSTS, or cut over production
   in this runbook. DNS/TLS and browser/WebSocket QA are separate stages.

## Subsequent code/data release sequence

For release `R2` while `current` is `R1`: take the required database backup,
stop the application on the minimum-capacity profile, prepare `R2` exactly
once, run compatible migrations/data import and pre-activation checks from
`R2`, then invoke `activate_release_ubuntu.sh --release-id R2 --confirm-ready R2`. Success yields
`current -> R2` and `previous -> R1`. Repeating activation for an already
healthy current release is a smoke-only no-op; it never rebuilds.

## Rollback and backups

Application rollback never changes database state:

```bash
sudo bash /opt/datosenorden/current/scripts/rollback_release_ubuntu.sh <PREVIOUS_RELEASE_ID>
```

Create a beta logical backup with restrictive permissions and a checksum:

```bash
sudo -u datosenorden env PGHOST=127.0.0.1 PGPORT=5432 \
  PGUSER=datosenorden_beta PGDATABASE=datosenorden_beta \
  bash /opt/datosenorden/current/scripts/backup_postgres.sh
```

Restore testing must use a new database first. Never restore over beta or
production as part of an application rollback.

## DNS handoff after technical smoke

Only after the technical staging gate: `A beta.datosenorden.cl -> TARGET_IPV4`.
Keep AAAA deferred until IPv6 is tested. Then verify DNS, HTTPS certificate,
headers, WebSocket, and public health checks before any apex-domain change.
