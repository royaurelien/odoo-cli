import click

from odoo_cli.cli.addons import (
    install_addons,
    list_addons,
    uninstall_addons,
    update_addons,
)
from odoo_cli.cli.backup import (
    clean_backups,
    list_backups,
    restore,
    restore_from_url,
    save,
)
from odoo_cli.cli.commands import (
    init_database,
    regenerate_assets,
    reload_configuration,
    reset_database,
    reset_master_password,
    restart,
    run_drop_database,
    run_shell,
    run_start,
    update_language,
    version,
)
from odoo_cli.cli.users import list_users, reset_password


@click.group()
def main():
    """Odoo CLI"""


main.add_command(clean_backups)
main.add_command(init_database)
main.add_command(install_addons)
main.add_command(list_addons)
main.add_command(list_backups)
main.add_command(list_users)
main.add_command(regenerate_assets)
main.add_command(reload_configuration)
main.add_command(reset_database)
main.add_command(reset_master_password)
main.add_command(reset_password)
main.add_command(restart)
main.add_command(restore_from_url)
main.add_command(restore)
main.add_command(run_drop_database)
main.add_command(run_shell)
main.add_command(run_start)
main.add_command(save)
main.add_command(uninstall_addons)
main.add_command(update_addons)
main.add_command(update_language)
main.add_command(version)
