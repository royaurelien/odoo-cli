import logging
import shutil
from contextlib import contextmanager

import odoo

try:
    from odoo import SUPERUSER_ID
except ImportError:
    from odoo import SUPERUSER_ID, models

    logging.info(
        f"Odoo >= 19 detected, importing {models.__name__} to support new namespace."
    )

from odoo_cli.utils import settings

_logger = logging.getLogger(__name__)


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


def find_odoo_bin():
    return shutil.which("odoo")


def get_version():
    return int(odoo.release.version[:2])


def get_default_admin_id():
    return 2 if int(odoo.release.version[:2]) > 11 else 1


def guess_admin_id(env=None):
    # src: odoo/addons/base/data/res_users_data.xml

    if env is None:
        return get_default_admin_id()

    try:
        if int(odoo.release.version[:2]) > 11:
            return env.ref("base.user_admin").id
        else:
            return env.ref("base.user_root").id
    except Exception:
        return get_default_admin_id()


def get_registry(version):
    if version >= 19:
        from odoo.modules.registry import Registry
    else:
        from odoo import registry as Registry

    return Registry


@contextmanager
def Environment(rollback=False, **kwargs):
    try:
        version = get_version()
        if version >= 15:
            Registry = get_registry(version)

            with Registry(settings.db_name).cursor() as cr:
                ctx = odoo.api.Environment(cr, SUPERUSER_ID, {})[
                    "res.users"
                ].context_get()
                env = odoo.api.Environment(cr, SUPERUSER_ID, ctx)

                yield env
                if rollback:
                    cr.rollback()
                else:
                    cr.commit()

        else:
            with odoo.api.Environment.manage():
                with odoo.sql_db.db_connect(settings.db_name).cursor() as cr:
                    ctx = odoo.api.Environment(cr, SUPERUSER_ID, {})[
                        "res.users"
                    ].context_get()
                    env = odoo.api.Environment(cr, SUPERUSER_ID, ctx)

                    yield env
                    if rollback:
                        cr.rollback()
                    else:
                        cr.commit()

    finally:
        # odoo.modules.registry.Registry.delete(database)
        odoo.sql_db.close_db(settings.db_name)
