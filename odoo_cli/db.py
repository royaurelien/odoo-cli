import logging
import os
from contextlib import contextmanager

import odoo

from odoo_cli.utils import get_env, settings

_logger = logging.getLogger(__name__)


@contextmanager
def db_management_enabled():
    old_params = {"list_db": odoo.tools.config["list_db"]}
    odoo.tools.config["list_db"] = True
    # Work around odoo.service.db.list_dbs() not finding the database
    # when postgres connection info is passed as PG* environment
    # variables.
    if odoo.release.version_info < (12, 0):
        for v in ("host", "port", "user", "password"):
            odoov = "db_" + v.lower()
            pgv = "PG" + v.upper()
            if not odoo.tools.config[odoov] and pgv in os.environ:
                old_params[odoov] = odoo.tools.config[odoov]
                odoo.tools.config[odoov] = os.environ[pgv]
    try:
        yield
    finally:
        for key, value in old_params.items():
            odoo.tools.config[key] = value


def list_databases():
    with db_management_enabled():
        return odoo.service.db.list_dbs()


def database_exists():
    return get_env()["db_name"] in list_databases()


def create_database(demo=True):
    with db_management_enabled():
        _logger.warning("Creating database %s", settings.db_name)
        odoo.service.db.exp_create_database(
            settings.db_name,
            demo,
            settings.lang,
            settings.user_password,
            settings.login,
            settings.country_code,
            phone=None,
        )


def drop_database():
    with db_management_enabled():
        _logger.warning("Dropping database %s", settings.db_name)
        odoo.service.db.exp_drop(settings.db_name)
