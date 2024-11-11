import click

from odoo_cli.backup import backup_database, list_backups
from odoo_cli.db import database_exists, drop_database


@click.command("backup")
@click.option("--filestore", is_flag=True, default=True, help="Include filestore")
def odoo_backup(filestore: bool):
    """Backup"""

    if database_exists():
        backup_database(filestore)


@click.command("restore")
@click.option(
    "--filestore/--no-filestore", is_flag=True, default=True, help="Include filestore"
)
@click.option(
    "--last", is_flag=True, default=False, help="Use the last backup available"
)
def odoo_restore(filestore: bool, last: bool):
    """Restore"""

    items = list_backups()
    choice = None
    if not items:
        click.echo("No backup found")
        return

    if last:
        choice = items[0]

    while choice is None:
        click.echo("Choose a backup to restore:")
        for i, item in enumerate(items):
            click.echo(f"{i}: {item['date']}, modules: {item['modules']}")
        choice = click.prompt("Choice", type=int, default=0)
        choice = items[choice] if 0 <= choice < len(items) else None

    if database_exists():
        drop_database()
