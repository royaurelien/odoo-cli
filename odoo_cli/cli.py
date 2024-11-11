import os

import click

from odoo_cli.common import find_odoo_bin, get_version
from odoo_cli.db import create_database, database_exists, drop_database, list_databases
from odoo_cli.utils import get_odoo_args


@click.group()
def main():
    """Odoo CLI"""


@click.command("start")
@click.option("--init", is_flag=True, default=True, help="Initialize the database")
def odoo_start(init):
    """Start"""

    if init and not database_exists():
        create_database()

    args = get_odoo_args([])
    os.execvp(find_odoo_bin(), ["odoo-bin"] + args)


@click.command("reset")
def odoo_reset():
    """Reset"""

    if database_exists():
        drop_database()

    create_database()


@click.command("shell")
def odoo_shell():
    """Reset"""
    cmd = [find_odoo_bin(), "shell", "-d", "test", "--no-http"]
    os.execv(cmd[0], cmd)


@click.command("version")
def odoo_version():
    """Odoo Version"""
    print(get_version())
    print(list_databases())


main.add_command(odoo_start)
main.add_command(odoo_reset)
main.add_command(odoo_backup)
main.add_command(odoo_restore)
main.add_command(odoo_shell)
main.add_command(odoo_version)
