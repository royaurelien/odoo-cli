import logging
import os
import random
import shutil
import signal
import string
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import odoo
import psycopg2

_logger = logging.getLogger("odoo")

DEFAULT_LANG = "fr_FR"
DEFAULT_COUNTRY = "fr"
DEFAULT_ADMIN_LOGIN = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"


@dataclass
class Settings:
    admin_login: str = os.getenv("ADMIN_LOGIN", DEFAULT_ADMIN_LOGIN)
    admin_password: str = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    lang: str = os.getenv("LANGUAGE", DEFAULT_LANG)
    country_code: str = os.getenv("COUNTRY", DEFAULT_COUNTRY)
    db_name: str = os.getenv("DATABASE", "test")
    core_count: str = os.getenv("CORE", "2")
    stage: str = os.getenv("STAGE", "dev")
    data_dir: str = "/var/lib/odoo"
    backup_path: str = "/var/lib/odoo/backups"
    db_host: str = os.getenv("HOST", "postgres")
    db_user: str = os.getenv("USER", "odoo")
    db_password: str = os.getenv("PASSWORD", "odoo")
    db_port: str = os.getenv("PORT", "5432")
    max_cron_threads: int = int(os.getenv("MAX_CRON_THREADS", "0"))
    workers: int = int(os.getenv("WORKERS", "0"))
    limit_memory_soft: int = int(os.getenv("LIMIT_MEMORY_SOFT", "629145600"))
    limit_memory_hard: int = int(os.getenv("LIMIT_MEMORY_HARD", "1677721600"))
    limit_time_cpu: int = int(os.getenv("LIMIT_TIME_CPU", "3200"))
    limit_time_real: int = int(os.getenv("LIMIT_TIME_REAL", "3200"))
    limit_time_real_cron: int = int(os.getenv("LIMIT_TIME_REAL_CRON", "3200"))
    limit_request: int = int(os.getenv("LIMIT_REQUEST", "8192"))
    addons_path = os.getenv("ADDONS_PATH", "/mnt/extra-addons")
    upgrade_path: str = os.getenv("UPGRADE_PATH", None)
    load: str = os.getenv("SERVER_WIDE_MODULES", "base,web")

    smtp_host: str = os.getenv("SMTP_HOST", None)
    smtp_port: str = os.getenv("SMTP_PORT", None)
    smtp_user: str = os.getenv("SMTP_USER", None)
    smtp_password: str = os.getenv("SMTP_PASSWORD", None)
    email_from: str = os.getenv("EMAIL_FROM", None)
    from_filter: str = os.getenv("FROM_FILTER", None)

    db_maxconn: int = int(os.getenv("DB_MAXCONN", "32"))
    pidfile: str = "/var/lib/odoo/odoo.pid"


settings = Settings()


def fix_addons_path() -> str:
    """
    Fix the addons path.
    """
    addons_path = odoo.tools.config["addons_path"].split(",")
    if settings.addons_path not in addons_path:
        addons_path.append(settings.addons_path)
    return ",".join(addons_path)


def get_pid(force: bool = False) -> Optional[int]:
    """
    Get the PID of the Odoo process.

    Returns:
    int: The PID of the Odoo process.
    """
    if force:
        return 1
    if not os.path.exists(settings.pidfile):
        return None
    with open(settings.pidfile, "r", encoding="utf-8") as f:
        return int(f.read().strip())


def restart_process(force: bool = False):
    # odoo.service.server.restart()
    pid = get_pid(force=force)
    if not pid:
        raise Exception("Odoo is not running")

    os.kill(pid, signal.SIGHUP)


def remove_dir(path):
    """
    Remove a directory and all its contents.

    Parameters:
    path (str): The path to the directory to be removed.

    Raises:
    FileNotFoundError: If the directory does not exist.
    PermissionError: If the user does not have permission to delete the directory.
    OSError: If an error occurs while deleting the directory.
    """
    shutil.rmtree(path)


def get_timestamp():
    """
    Get the current timestamp in UTC as a string.

    Returns:
        str: The current timestamp in UTC as a string.
    """
    return str(int(datetime.now(timezone.utc).timestamp()))


def get_datetime(timestamp):
    """
    Convert a Unix timestamp to a formatted datetime string in UTC.

    Args:
        timestamp (int or str): The Unix timestamp to convert.

    Returns:
        str: The formatted datetime string in the format "%Y-%m-%d %H:%M:%S" in UTC.
    """
    return datetime.fromtimestamp(int(timestamp), timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def random_password(length=12):
    """Generate a random password of given length."""

    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(random.choice(characters) for i in range(length))
    return password


def get_odoo_args(args, database: bool = True, dev: bool = False, safe: bool = True):
    """
    Generate a list of Odoo command-line arguments based on the provided settings and input arguments.

    Args:
        args (list): A list of initial command-line arguments.
        database (bool, optional): Whether to include the database argument. Defaults to True.
        dev (bool, optional): Whether to include development-specific arguments. Defaults to False.

    Returns:
        list: A list of command-line arguments for Odoo.
    """
    odoo_args = [
        "--unaccent",
        "--db_host",
        settings.db_host,
        f"--db_port={settings.db_port}",
        f"--db_user={settings.db_user}",
        f"--db_password={settings.db_password}",
        "--db-filter=",
        "--data-dir",
        settings.data_dir,
        f"--max-cron-threads={settings.max_cron_threads}",
        f"--workers={settings.workers}",
        f"--db_maxconn={settings.db_maxconn}",
        f"--limit-memory-soft={settings.limit_memory_soft}",
        f"--limit-memory-hard={settings.limit_memory_hard}",
        f"--limit-time-cpu={settings.limit_time_cpu}",
        f"--limit-time-real={settings.limit_time_real}",
        f"--limit-time-real-cron={settings.limit_time_real_cron}",
        f"--limit-request={settings.limit_request}",
        f"--load={settings.load}",
        f"--pidfile={settings.pidfile}",
    ]

    if dev:
        odoo_args.extend(["--dev=reload"])

    if safe:
        odoo_args.extend(["--no-database-list"])

    if settings.smtp_host and settings.smtp_port:
        odoo_args.extend(
            ["--smtp", settings.smtp_host, "--smtp-port", settings.smtp_port]
        )

        if settings.smtp_user and settings.smtp_password:
            odoo_args.extend(
                [
                    "--smtp-user",
                    settings.smtp_user,
                    "--smtp-password",
                    settings.smtp_password,
                ]
            )

        if settings.email_from:
            odoo_args.extend(["--email-from", settings.email_from])

        if settings.from_filter:
            odoo_args.extend(["--from-filter", settings.from_filter])

    if not any(arg.startswith("--database") for arg in args) and database:
        odoo_args.extend(["--database", settings.db_name])
    if (
        not any(arg.startswith("--without-demo") for arg in args)
        and settings.stage != "dev"
    ):
        odoo_args.append("--without-demo=all")
    return args + odoo_args


def wait_for_psql(timeout=30):
    """
    Wait for the PostgreSQL server to start.
    """
    _logger.info(settings)
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            _logger.info("Trying to connect to the database...")
            conn = psycopg2.connect(
                user=settings.db_user,
                host=settings.db_host,
                port=settings.db_port,
                password=settings.db_password,
                dbname="postgres",
            )
            error = ""
            break
        except psycopg2.OperationalError as e:
            error = e
        else:
            conn.close()
        time.sleep(1)

    if error:
        _logger.error("Database connection failure: %s", error)
        sys.exit(1)
