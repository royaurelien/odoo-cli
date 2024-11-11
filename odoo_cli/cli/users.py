import click

from odoo_cli.common import get_admin_id
from odoo_cli.db import (
    Environment,
)
from odoo_cli.utils import settings


@click.command("reset-password")
def reset_password():
    """Reset admin password"""
    with Environment() as env:
        env["res.users"].browse(get_admin_id()).write(
            {
                "login": settings.login,
                "password": settings.user_password,
                "active": True,
            }
        )
        click.echo("Password reset for user %s", settings.login)


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
