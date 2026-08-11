# VPS Go-Live Steps

This runbook deploys an immutable public release to Ubuntu 24.04 LTS. It does
not deploy from a mutable clone, and it does not contain credentials.

## Preconditions

- The target is a verified Ubuntu 24.04 VPS with at least 3 vCPU, about 8 GB
  RAM, and 75 GB NVMe storage.
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
5. **MANUAL/GATE**: create a mode-0600 password file outside the release, then
   execute `configure_postgres_beta.sh` from the verified artifact with the
   password-file path. PostgreSQL must remain loopback-only.
6. **AUTOMATED**: prepare the immutable release from the same artifact:

   ```bash
   tar -xOf /secure-upload/datosenorden.tar scripts/deploy_release_ubuntu.sh | sudo bash -s -- \
     --artifact /secure-upload/datosenorden.tar \
     --sha256 <ARTIFACT_SHA256> \
     --release-id <RELEASE_ID>
   ```

   The command prepares but does not activate a release. It fails closed on a
   checksum, archive, dependency, or Reflex build failure.
7. **GATE**: extract only `deployment/datosenorden.service` and
   `deployment/Caddyfile` from the verified artifact into their system
   locations, then validate them.
   Validate with `systemd-analyze verify /etc/systemd/system/datosenorden.service`
   and `caddy validate --config /etc/caddy/Caddyfile` before enabling services.
8. **AUTOMATED**: repeat the deployment command with `--activate`, then run
   `sudo systemctl daemon-reload && sudo systemctl enable --now datosenorden`.
9. **GATE**: execute `post_deploy_smoke.sh` from the verified artifact against
   `<RELEASE_ID>`.
   It verifies the service, loopback app/database, current symlink, and that
   ports 3000 and 5432 are not public bindings.
10. **STOP**: do not create the DNS record, enable HSTS, or cut over production
   in this runbook. DNS/TLS and browser/WebSocket QA are separate stages.

## Rollback and backups

Application rollback never changes database state:

```bash
sudo bash scripts/rollback_release_ubuntu.sh <PREVIOUS_RELEASE_ID>
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
