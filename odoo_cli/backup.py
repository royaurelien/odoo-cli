import json
import logging
import os
import shutil
import subprocess

import odoo

from odoo_cli.db import db_management_enabled
from odoo_cli.utils import _get_datetime, _get_timestamp, settings

_logger = logging.getLogger(__name__)


def _get_backup_path():
    root = os.path.join(settings.backup_path, _get_timestamp())
    os.makedirs(root, exist_ok=True)
    return root, os.path.join(root, "dump")


def list_backups():
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
                        "date": _get_datetime(item),
                        "filestore": "filestore" in contents,
                        "path": path,
                        "modules": modules,
                    }
                )
    items.sort(key=lambda x: x["name"], reverse=True)
    return items


def backup_database(filestore=True):
    """
    Backup the Odoo database and optionally its filestore.
    This function creates a backup of the specified Odoo database by dumping
    its contents and optionally copying its filestore. The backup includes a
    manifest file with metadata about the database.
    Args:
        filestore (bool): If True, the filestore associated with the database
                          will also be backed up. Defaults to True.
    Raises:
        Exception: If an error occurs during the backup process, the exception
                   is logged, the backup directory is removed, and the error
                   is re-raised.
    Side Effects:
        - Creates a backup directory containing the database dump and manifest file.
        - Optionally copies the filestore to the backup directory.
        - Logs warnings and errors related to the backup process.
    """

    print(settings)
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
            _logger.warning("Copying filestore to %s", path)
            fs = odoo.tools.config.filestore(settings.db_name)
            shutil.copytree(fs, os.path.join(path, "filestore"))

    except Exception as error:
        _logger.error("Error while backing up database %s: %s", settings.db_name, error)
        shutil.rmtree(path)
        raise error
    finally:
        odoo.sql_db.close_db(settings.db_name)


def restore_database(dump_name):
    """
    Restore the upgraded database locally using 'core_count' CPU to reduce the restoring time.
    """
    _logger.info(
        "Restore the dump file '%s' as the database '%s'", dump_name, settings.db_name
    )

    try:
        subprocess.check_output(
            ["createdb", settings.db_name], stderr=subprocess.STDOUT
        )
        subprocess.check_output(
            [
                "pg_restore",
                "--no-owner",
                "--format",
                "d",
                dump_name,
                "--dbname",
                settings.db_name,
                "--jobs",
                settings.core_count,
            ],
            stderr=subprocess.STDOUT,
        )
    except Exception as error:
        _logger.error("Error while restoring the database: %s", error)
        raise error


# def restore_filestore(origin_db_name, upgraded_db_name):
#     """
#     Restore the new filestore by merging it with the old one, in a folder named
#     as the upgraded database.
#     If the previous filestore is not found, the new filestore should be restored manually.
#     """
#     if not origin_db_name:
#         logging.warning(
#             "The original filestore location could not be determined."
#             " The filestore of the upgrade database should be restored manually."
#         )
#         return

#     origin_fs_path = os.path.join(FILESTORE_PATH, origin_db_name)

#     if os.path.exists(origin_fs_path):
#         new_fs_path = os.path.join(FILESTORE_PATH, upgraded_db_name)

#         logging.info(
#             "Merging the new filestore with the old one in %s ...", new_fs_path
#         )
#         shutil.copytree(origin_fs_path, new_fs_path)
#         if os.path.isdir(FILESTORE_NAME):
#             run_command(["rsync", "-a", FILESTORE_NAME + os.sep, new_fs_path])
#             shutil.rmtree(FILESTORE_NAME)
#     else:
#         logging.warning(
#             "The original filestore of '%s' has not been found in %s. "
#             "The filestore of the upgrade database should be restored manually.",
#             origin_db_name,
#             FILESTORE_PATH,
#         )
