import os
import sys

import click

from odoo_cli.common import Environment, find_odoo_bin, settings
from odoo_cli.db import uninstall
from odoo_cli.utils import restart_process


def _parse_inputs(raw):
    return list(set(map(str.strip, raw.split(","))))


@click.command("install")
@click.argument("modules", default="local")
@click.option("--restart", is_flag=True, help="Restart Odoo")
def install_addons(modules: str, restart: bool):
    """Install addons"""

    modules = _parse_inputs(modules)
    cmd = [
        find_odoo_bin(),
        "-d",
        settings.db_name,
        "--stop-after-init",
        "--no-http",
        "-i",
        ",".join(modules),
    ]
    os.execv(cmd[0], cmd)

    if restart:
        try:
            restart_process(force=True)
        except Exception as error:
            click.echo(error)
            sys.exit(1)


@click.command("update")
@click.argument("modules", default="local")
@click.option("--restart", is_flag=True, help="Restart Odoo")
def update_addons(modules: str, restart: bool):
    """Update addons"""

    modules = _parse_inputs(modules)
    cmd = [
        find_odoo_bin(),
        "-d",
        settings.db_name,
        "--stop-after-init",
        "--no-http",
        "-u",
        ",".join(modules),
    ]
    os.execv(cmd[0], cmd)

    if restart:
        try:
            restart_process(force=True)
        except Exception as error:
            click.echo(error)
            sys.exit(1)


@click.command("uninstall")
@click.argument("modules")
def uninstall_addons(modules: str):
    """Uninstall addons"""

    modules = _parse_inputs(modules)
    uninstall(modules)


@click.option("--export", is_flag=True, help="Ready to export")
@click.command("list-addons")
def list_addons(export: bool):
    """List addons"""

    with Environment() as env:
        domain = [
            ("application", "=", True),
            ("state", "in", ["installed", "to upgrade", "to remove"]),
        ]
        apps = env["ir.module.module"].sudo().search_read(domain, ["name"])
        apps = sorted([apps["name"] for apps in apps])
        click.echo(f"Applications ({len(apps)}): {', '.join(apps)}")

        domain = [
            ("state", "in", ["installed", "to upgrade", "to remove"]),
        ]
        addons = (
            env["ir.module.module"]
            .sudo()
            .search_read(domain, ["name", "installed_version"])
        )
        addons.sort(key=lambda x: x["name"])

        click.echo(f"{len(addons)} addons installed")

        if not addons:
            return 0

        if export:
            output = ",".join(map(lambda item: item["name"], addons))
            click.echo(output)
            return 0

        for addon in addons:
            click.echo(f"\t{addon['name']} ({addon['installed_version']})")
