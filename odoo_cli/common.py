import logging
import shutil

import odoo

_logger = logging.getLogger(__name__)


def find_odoo_bin():
    return shutil.which("odoo")


def get_version():
    return int(odoo.release.version[:2])
