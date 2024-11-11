import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone

DEFAULT_LANG = "fr_FR"
DEFAULT_COUNTRY = "fr"


@dataclass
class Settings:
    user_password: str = os.getenv("ADMIN_PASSWORD", "admin")
    login: str = os.getenv("ADMIN_LOGIN", "admin")
    lang: str = os.getenv("LANGUAGE", DEFAULT_LANG)
    country_code: str = os.getenv("COUNTRY", DEFAULT_COUNTRY)
    db_name: str = os.getenv("DATABASE", "test")
    core_count: str = os.getenv("CORE", "2")
    stage: str = os.getenv("STAGE", "dev")
    backup_path: str = "/var/lib/odoo/backups"


settings = Settings()


def remove_dir(path):
    shutil.rmtree(path)


def _get_timestamp():
    """
    Get the current timestamp in UTC as a string.

    Returns:
        str: The current timestamp in UTC as a string.
    """
    return str(int(datetime.now(timezone.utc).timestamp()))


def _get_datetime(timestamp):
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


def get_odoo_args(args):
    print(args)

    odoo_args = [
        # "--addons-path",
        # os.getenv("ADDONS_PATH", "/mnt/extra-addons"),
        "--unaccent",
        "--no-database-list",
        "--proxy-mode",
        "--geoip-db=/usr/share/GeoIP/GeoLite2-City.mmdb",
        "--db_host",
        os.getenv("HOST", "localhost"),
        "--db_port=5432",
        "--db-filter=",
        # "--smtp",
        # os.environ["SMTP_HOST"],
        # "--smtp-port",
        # os.environ["SMTP_PORT"],
        "--data-dir",
        "/var/lib/odoo",
        "--config",
        "/etc/odoo/odoo.conf",
        "--workers=0",
    ]
    if not any(arg.startswith("--database") for arg in args):
        odoo_args.extend(["--database", os.environ["PGDATABASE"]])
    if not any(arg.startswith("--db_maxconn") for arg in args):
        odoo_args.append("--db_maxconn=16")
    if (
        not any(arg.startswith("--without-demo") for arg in args)
        and os.environ["ODOO_STAGE"] != "dev"
    ):
        odoo_args.append("--without-demo=all")
    return args + odoo_args
