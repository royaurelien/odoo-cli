import click

from odoo_cli.backup import (
    get_backups,
    restore_database,
    save_database,
)
from odoo_cli.common import abort_if_false
from odoo_cli.db import database_exists, drop_database
from odoo_cli.utils import remove_dir


@click.command("save")
@click.option("--filestore", is_flag=True, default=True, help="Include filestore")
def save(filestore: bool):
    """Create a database backup"""

    if database_exists():
        save_database(filestore)


@click.command("restore")
@click.option(
    "--filestore/--no-filestore", is_flag=True, default=True, help="Include filestore"
)
@click.option(
    "--neutralize/--no-neutralize",
    is_flag=True,
    default=True,
    help="Neutralize database",
)
@click.option(
    "--last", is_flag=True, default=False, help="Use the last backup available"
)
def restore(filestore: bool, neutralize: bool, last: bool):
    """Restore"""

    items = get_backups()
    choice = None
    if not items:
        click.echo("No backup found")
        return

    if last:
        choice = items[0]

    while choice is None:
        click.echo("Choose a backup to restore:")
        for i, item in enumerate(items):
            click.echo(
                f"{i}: {item['date']}, modules: {item['modules']}, filestore: {item['filestore']}"
            )
        choice = click.prompt("Choice", type=int, default=0)
        choice = items[choice] if 0 <= choice < len(items) else None

    if database_exists():
        drop_database()

    restore_database(choice, filestore, neutralize)


@click.command("restore-url")
@click.argument("url")
def restore_from_url(url: str):
    """Download and restore a backup from a URL"""


@click.command("clean")
@click.option(
    "--yes",
    is_flag=True,
    callback=abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to delete all the backups?",
)
def clean_backups():
    """Clean backups"""

    for item in get_backups():
        remove_dir(item["path"])


@click.command("list-backups")
def list_backups():
    """List local backups"""

    items = get_backups()

    click.echo(f"Backups {len(items)}:")
    for i, item in enumerate(items):
        click.echo(
            f"{i}: {item['date']}, modules: {item['modules']}, filestore: {item['filestore']}"
        )
