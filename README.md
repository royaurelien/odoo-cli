# Odoo CLI

Odoo CLI is a thin management layer around the standard `odoo` executable. It
streamlines the workflows that a developer or operator typically performs when
working with self-managed Odoo instances: starting the server, preparing a fresh
schema, installing addons, refreshing data, or handling backups. The project is
implemented on top of [Click](https://click.palletsprojects.com/) so every
command is discoverable with built-in `--help` documentation.

## Features
- Run or restart an Odoo server with consistent environment defaults.
- Create, reset, drop, and introspect the working database.
- Install, update, uninstall, and list addons that are deployed on the
  instance.
- Manage backups, including creating and restoring dumps and filestores.
- Reset credentials, languages, assets, and other maintenance tasks.

## Requirements
- Python 3.7 or later.
- A working Odoo installation; the `odoo` binary must be on the `PATH`.
- Access to the PostgreSQL server that hosts your Odoo databases.

## Installation
- **From source**:
  ```bash
  git clone https://github.com/<your-org>/odoo-cli.git
  cd odoo-cli
  pip install .
  ```
- **With Poetry** (for development):
  ```bash
  poetry install
  poetry run odoo-cli --help
  ```

`odoo-cli` is exposed via the Poetry script entry point, so once the package is
installed you can run `odoo-cli` directly from any shell session that inherits
the Python environment.

## Configuration
Runtime behaviour is controlled through environment variables that are read when
a command starts. Defaults are chosen for local development and can be adapted
to match staging or production deployments.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE` | `test` | Database name managed by the CLI. |
| `HOST` | `postgres` | PostgreSQL host name. |
| `PORT` | `5432` | PostgreSQL port. |
| `USER` | `odoo` | PostgreSQL user. |
| `PASSWORD` | `odoo` | PostgreSQL password. |
| `ADMIN_LOGIN` | `admin` | Admin login written during database creation/reset. |
| `ADMIN_PASSWORD` | `admin` | Admin password used by reset commands. |
| `LANGUAGE` | `fr_FR` | Default language installed during initialisation. |
| `COUNTRY` | `fr` | Country code applied to the company profile. |
| `CORE` | `2` | Number of parallel jobs used by `pg_dump`/`pg_restore`. |
| `STAGE` | `dev` | Set to something else to automatically disable demo data. |
| `MAX_CRON_THREADS` | `0` | Passed to Odoo as `--max-cron-threads`. |
| `WORKERS` | `0` | Passed to Odoo as `--workers`. |
| `DB_MAXCONN` | `32` | Maximum PostgreSQL connections. |
| `LIMIT_MEMORY_SOFT` | `629145600` | Soft memory limit for workers (bytes). |
| `LIMIT_MEMORY_HARD` | `1677721600` | Hard memory limit for workers (bytes). |
| `LIMIT_TIME_CPU` | `3200` | CPU time limit per request. |
| `LIMIT_TIME_REAL` | `3200` | Wall-clock time limit per request. |
| `LIMIT_TIME_REAL_CRON` | `3200` | Wall-clock limit for cron jobs. |
| `LIMIT_REQUEST` | `8192` | Request limit per worker. |
| `SERVER_WIDE_MODULES` | `base,web` | Value passed to `--load`. |
| `ADDONS_PATH` | `/mnt/extra-addons` | Extra addons path appended to config. |
| `UPGRADE_PATH` | _empty_ | Optional path with upgrade scripts. |
| `SMTP_HOST` / `SMTP_PORT` | _empty_ | SMTP endpoint injected into config. |
| `SMTP_USER` / `SMTP_PASSWORD` | _empty_ | SMTP auth pair if required. |
| `EMAIL_FROM` | _empty_ | Default outbound email address. |
| `FROM_FILTER` | _empty_ | SMTP from-address filter. |

Other internal defaults: data is stored under `/var/lib/odoo`, backups are
written to `/var/lib/odoo/backups`, and the PID file is expected at
`/var/lib/odoo/odoo.pid`. Override these by exporting new values before running
the CLI.

## Usage
- Inspect the available commands: `odoo-cli --help`.
- Commands can be explored individually: `odoo-cli <command> --help`.
- For shells that support Click completion, run:
  ```bash
  eval "$(odoo-cli --show-completion zsh)"
  ```
  Replace `zsh` with your shell name (`bash`, `fish`, ...) if needed.

Most operations expect that Odoo has already been configured to point to the
PostgreSQL server described by the environment variables above.

## Command Reference
The CLI groups commands in logical areas. Each command accepts `--help` for more
details.

### Core Server Operations
- `odoo-cli start [--dev] [--force-db] [--unsafe] [--log-level=<level>]`
  - Starts the Odoo server using the computed configuration. `--dev` injects
    development flags, `--force-db` ensures the configured database exists
    before the server starts, `--unsafe` skips the safety guard that hides the
    database list, and `--log-level` accepts one of:
    `info`, `debug`, `debug_sql`, `debug_rpc`, `debug_rpc_answer`, `error`,
    `critical`, `warn`, `test`, `runbot`, or `notset`.
- `odoo-cli reload-conf`
  - Rebuilds `odoo.conf` from environment variables and prints the resulting
    configuration.
- `odoo-cli restart [--force]`
  - Sends `SIGHUP` to the running Odoo process referenced by the PID file.
    `--force` assumes the process runs as PID 1 (useful in container setups).
- `odoo-cli shell`
  - Opens an interactive Odoo shell against the configured database without
    starting the HTTP server.
- `odoo-cli version`
  - Prints the detected Odoo major version number.

### Database Lifecycle
- `odoo-cli init`
  - Creates the database if it does not exist yet.
- `odoo-cli reset`
  - Drops the database if present and re-creates it from scratch.
- `odoo-cli drop`
  - Drops the database without recreating it.
- `odoo-cli update-language`
  - Installs the language defined by `LANGUAGE`, activates it on all users, and
    aligns the company address, currency, and time zones with `COUNTRY`.
- `odoo-cli regenerate-assets`
  - Deletes auto-generated CSS and JS attachments so that Odoo rebuilds assets
    on the next load.
- `odoo-cli reset-master-password`
  - Generates a new random master password, updates `odoo.conf`, and prints the
    value along with the current configuration summary.

### Addons Management
- `odoo-cli install [MODULES] [--restart]`
  - Installs one or more addons using the `odoo` binary with
    `--stop-after-init`. Pass a comma-separated list or rely on the `local`
    default to install the local module.
- `odoo-cli update [MODULES] [--restart]`
  - Runs an addon upgrade (`-u`) for the given modules.
- `odoo-cli uninstall MODULES`
  - Removes addons using the ORM (`button_immediate_uninstall`).
- `odoo-cli list-addons [--export]`
  - Lists installed addons. Use `--export` to output a comma-separated list that
    can be reused with the install or update commands.

### Backup Management
- `odoo-cli save [--filestore]`
  - Creates a timestamped backup under `BACKUP_PATH`. Filestore contents are
    included by default.
- `odoo-cli restore [--filestore/--no-filestore] [--neutralize/--no-neutralize] [--last]`
  - Restores a backup selected interactively (or the most recent one with
    `--last`). Neutralisation disables outgoing mail servers and cron jobs by
    default.
- `odoo-cli restore-url URL`
  - Placeholder for restoring a backup fetched from a remote URL. Implement the
    download logic before using it in production.
- `odoo-cli clean [--yes]`
  - Deletes every backup directory after an explicit confirmation.
- `odoo-cli list-backups`
  - Displays the backups discovered under `BACKUP_PATH` with metadata such as
    creation time and module count.

### User Management
- `odoo-cli reset-password [--random]`
  - Resets the administrator account using `ADMIN_LOGIN` and `ADMIN_PASSWORD`.
    Add `--random` to generate a random password instead.
- `odoo-cli list-users [--active/--no-active] [--admin]`
  - Lists internal users. The command lists only active users by default; add
    `--no-active` to include deactivated users and `--admin` to show only
    administrators.

## Development
Run the test suite (when available) from the project root:
```bash
poetry run pytest
```

Pull requests and issues are welcome. Please describe your environment and the
command you were running when reporting problems.
