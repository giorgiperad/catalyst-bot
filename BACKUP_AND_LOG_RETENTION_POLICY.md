# Backup and Log Retention Policy

This document governs the retention, rotation, and deletion of database backups, runtime logs, and related artifacts for the Chia Market Maker bot.

**Rule: Destructive deletion of database backups or runtime logs requires explicit operator confirmation. Automated cleanup tools and audit processes must not delete these files without asking first.**

---

## Database Backups (`bot_backup_*.db`)

| Retention tier | Period | Action |
|---------------|--------|--------|
| Hot (root directory) | Last 7 days | Keep in place for quick rollback |
| Warm (archive) | 7-30 days | Move to `_archive/` with dated subfolder |
| Cold | 30+ days | Operator decides: keep, compress, or delete |

- The bot creates timestamped backups automatically.
- At least the **3 most recent backups** must always be retained regardless of age.
- Before any bulk deletion, verify the live `bot.db` is healthy and the most recent backup is readable.
- Never delete all backups in a single operation.

## Runtime Logs (`bot_superlog_*.log`)

| Retention tier | Period | Action |
|---------------|--------|--------|
| Active | Current session | Never delete while bot is running |
| Recent | Last 14 days | Keep for forensic investigation |
| Archived | 14+ days | Move to `_archive/` or compress |

- Logs from a running bot process must never be targeted for deletion.
- Historical logs have forensic value for diagnosing fills, coin losses, and wallet issues.

## Other Runtime Artifacts

| File | Retention | Notes |
|------|-----------|-------|
| `coin_prep_output.log` | Regenerable | Safe to delete; recreated on next coin prep |
| `coin_prep_status.json` | Regenerable | Runtime state; recreated on start |
| `coin_prep_last.json` | Regenerable | Runtime state; recreated on start |
| `designation_debug.json` | Keep 7 days | Diagnostic; useful for debugging coin designation |
| `worker_cancelled_ids.json` | Regenerable | Runtime state |
| `tauri_backend_stdout.log` | Regenerable | Tauri-era artifact; safe to delete |
| `.tauri-instance.lock` | Ephemeral | Safe to delete when no Tauri process is running |

## Build Artifacts

| Directory | Retention | Notes |
|-----------|-----------|-------|
| `src-tauri/target/` | Regenerable | Rust build cache; `cargo build` recreates |
| `_tauri_release*/` | Regenerable | Release build output; rebuilds recreate |
| `t/` | Regenerable | Stale build cache; safe to delete |
| `__pycache__/` | Regenerable | Python bytecode cache |
| `tmp_db_*/` | Ephemeral | Temp DB directories; safe when process isn't running |

## Source Code Backups (`_backups/`)

- The `_backups/` directory contains `.bak` snapshots of every core module.
- **Keep indefinitely** as a rollback safety net until the project uses proper version control.
- These are small (2.7MB total) and cost nothing to retain.

## Archive (`_archive/`)

- Contains historical DB backups and logs.
- **Keep indefinitely** or until the operator reviews and decides.
- Do not delete without operator confirmation.

## Operator Notes

| File | Retention | Notes |
|------|-----------|-------|
| `overnight_bot_watch.md` | Keep | Valuable operational history |
| `overnight_log_watch.md` | Keep | Valuable operational history |

## Rules for Automated Tools and Audit Processes

1. **Never delete database backups without explicit operator confirmation.**
2. **Never delete logs from a running bot process.**
3. **When cleaning up, move to `_archive/` rather than deleting.**
4. **Always keep at least 3 recent backups and 14 days of logs.**
5. **Build artifacts and `__pycache__` may be deleted freely.**
6. **When in doubt, ask the operator.**
