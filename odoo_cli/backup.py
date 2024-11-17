import json
import logging
import os
import shutil
import subprocess

import odoo

from odoo_cli.db import db_management_enabled, init_database
from odoo_cli.utils import get_datetime, get_timestamp, settings

_logger = logging.getLogger(__name__)


def _get_backup_path():
    root = os.path.join(settings.backup_path, get_timestamp())
    os.makedirs(root, exist_ok=True)
    return root, os.path.join(root, "dump")


def get_backups():
    """
    List all available backups in the backup directory.

    This function scans the backup directory specified in the settings,
    identifies valid backups by checking for the presence of "dump" and
    "manifest.json" files, and returns a list of dictionaries containing
    information about each backup.

        list: A list of dictionaries, each containing the following keys:
            - name (str): The name of the backup directory.
            - date (datetime): The datetime object representing the backup date.
            - filestore (bool): Whether the backup contains a filestore.
            - path (str): The full path to the backup directory.
    """
    items = []
    for item in os.listdir(settings.backup_path):
        path = os.path.join(settings.backup_path, item)
        if os.path.isdir(path):
            contents = os.listdir(path)
            if "dump" in contents and "manifest.json" in contents:
                with open(os.path.join(path, "manifest.json"), "r") as f:
                    manifest = json.load(f)
                    modules = len(manifest.get("modules"))
                items.append(
                    {
                        "name": item,
                        "date": get_datetime(item),
                        "filestore": "filestore" in contents,
                        "path": path,
                        "dump": os.path.join(path, "dump"),
                        "modules": modules,
                    }
                )
    items.sort(key=lambda x: x["name"], reverse=True)
    return items


def save_database(filestore=True):
    path, dump = _get_backup_path()
    db = odoo.sql_db.db_connect(settings.db_name)

    try:
        with db.cursor() as cr, db_management_enabled():
            env = odoo.tools.misc.exec_pg_environ()
            # print(env)

            _logger.warning("Writing manifest to %s", path)
            with open(os.path.join(path, "manifest.json"), "w") as f:
                manifest = odoo.service.db.dump_db_manifest(cr)
                json.dump(manifest, f, indent=4)

            _logger.warning("Backing up database %s to %s", settings.db_name, dump)
            subprocess.check_output(
                [
                    "pg_dump",
                    "--no-owner",
                    "--format",
                    "d",
                    "--jobs",
                    settings.core_count,
                    "--file",
                    dump,
                    settings.db_name,
                ],
                stderr=subprocess.STDOUT,
                env=env,
            )

        if filestore:
            fs = odoo.tools.config.filestore(settings.db_name)
            if os.path.exists(fs):
                _logger.warning("Copying filestore to %s", path)
                shutil.copytree(fs, os.path.join(path, "filestore"))

    except Exception as error:
        _logger.error("Error while backing up database %s: %s", settings.db_name, error)
        shutil.rmtree(path)
        raise error
    finally:
        odoo.sql_db.close_db(settings.db_name)


def restore_database(backup: dict, filestore: bool = True, neutralize: bool = True):
    """
    Restore the upgraded database locally using 'core_count' CPU to reduce the restoring time.
    """
    _logger.info(
        "Restore the dump file '%s' as the database '%s'",
        backup["dump"],
        settings.db_name,
    )

    odoo.service.db._create_empty_database(settings.db_name)
    env = odoo.tools.misc.exec_pg_environ()
    try:
        subprocess.check_output(
            [
                "pg_restore",
                "--no-owner",
                "--format",
                "d",
                backup["dump"],
                "--dbname",
                settings.db_name,
                "--jobs",
                settings.core_count,
            ],
            stderr=subprocess.STDOUT,
            env=env,
        )
    except Exception as error:
        _logger.error("Error while restoring the database: %s", error)
        with db_management_enabled():
            odoo.service.db.exp_drop(settings.db_name)
        raise error

    init_database(neutralize)

    if filestore and backup["filestore"]:
        from_fs = os.path.join(backup["path"], "filestore")
        to_fs = odoo.tools.config.filestore(settings.db_name)
        if os.path.exists(from_fs) and not os.path.exists(to_fs):
            shutil.copytree(from_fs, to_fs)
