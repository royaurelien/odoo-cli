import logging
import os
from contextlib import contextmanager

import odoo
from odoo import SUPERUSER_ID

from odoo_cli.common import Environment
from odoo_cli.utils import settings

_logger = logging.getLogger(__name__)

SQL_RESET_CONFIG_PARAMETERS = """
DELETE FROM ir_config_parameter
WHERE key = 'database.enterprise_code';

UPDATE ir_config_parameter
SET value = 'copy'
WHERE key = 'database.expiration_reason'
AND value != 'demo';

UPDATE ir_config_parameter
SET value = CURRENT_DATE + INTERVAL '2 month'
WHERE key = 'database.expiration_date';

"""
SQL_NEUTRALIZE_DATABASE = """
UPDATE fetchmail_server
   SET active = false;
                          
UPDATE ir_mail_server
   SET active = false;

-- insert dummy mail server to prevent using fallback servers specified using command line
INSERT INTO ir_mail_server(name, smtp_port, smtp_host, smtp_encryption, active, smtp_authentication)
VALUES ('neutralization - disable emails', 1025, 'invalid', 'none', true, 'login');

-- deactivate crons
UPDATE ir_cron
   SET active = false
 WHERE id NOT IN (
       SELECT res_id
         FROM ir_model_data
        WHERE model = 'ir.cron'
          AND name = 'autovacuum_job'
);                       
"""
SQL_NEUTRALIZE_FETCHMAIL = "UPDATE fetchmail_server SET active = false;"


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


def _neutralize_database(cursor):
    if odoo.release.version_info >= (16, 0):
        odoo.modules.neutralize.neutralize_database(cursor)
        cursor.execute(SQL_NEUTRALIZE_FETCHMAIL)
    else:
        cursor.execute(SQL_NEUTRALIZE_DATABASE)


def neutralize_database():
    registry = odoo.modules.registry.Registry.new(settings.db_name)
    with registry.cursor() as cr:
        _neutralize_database(cr)


def _reset_config_parameters(cursor):
    cursor.execute(SQL_RESET_CONFIG_PARAMETERS)


def list_databases():
    with db_management_enabled():
        return odoo.service.db.list_dbs()


def database_exists():
    return settings.db_name in list_databases()


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


def init_database(neutralize=True):
    registry = odoo.modules.registry.Registry.new(settings.db_name)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        env["ir.config_parameter"].init(force=True)

        _reset_config_parameters(cr)

        if neutralize:
            _neutralize_database(cr)


def uninstall(items):
    with Environment() as env:
        modules = env["ir.module.module"].search([("name", "in", items)])
        _logger.info("Uninstalling %s", modules.mapped("name"))
        modules.button_immediate_uninstall()
        env.cr.commit()
