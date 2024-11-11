import click

from odoo_cli.cli.backup import odoo_backup, odoo_restore
from odoo_cli.cli.commands import odoo_reset, odoo_shell, odoo_start, odoo_version


@click.group()
def main():
    """Odoo CLI"""


main.add_command(odoo_start)
main.add_command(odoo_reset)
main.add_command(odoo_backup)
main.add_command(odoo_restore)
main.add_command(odoo_shell)
main.add_command(odoo_version)
