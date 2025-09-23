import click

from odoo_cli.common import guess_admin_id
from odoo_cli.db import (
    Environment,
)
from odoo_cli.utils import random_password, settings


@click.command("reset-password")
@click.option("--random", is_flag=True, help="Generate a random password")
def reset_password(random: bool):
    """Reset admin password"""
    with Environment() as env:
        env["res.users"].browse(guess_admin_id(env)).write(
            {
                "login": settings.admin_login,
                "password": settings.admin_password
                if not random
                else random_password(),
                "active": True,
            }
        )
        click.echo(f"Password admin password with: {settings.admin_password}")


@click.command("list-users")
@click.option(
    "--active/--no-active", is_flag=True, default=True, help="List active users only"
)
@click.option("--admin", is_flag=True, default=False, help="List admin users only")
def list_users(active: bool, admin: bool):
    """List users"""

    with Environment() as env:
        records = env["res.users"].with_context(active_test=active).search([])
        users = records.filtered(lambda record: record._is_internal())

        if admin:
            users = users.filtered(lambda record: record._is_admin())

        users = users.read(["name", "login", "email", "active"])

        click.echo(f"Users ({len(users)}):")
        for user in users:
            click.echo(f"  {user['name']} ({user['login']})")
            click.echo(f"     email: {user['email']}")
            click.echo(f"     active: {user['active']}")
            click.echo()
