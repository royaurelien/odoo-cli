import os

import click
import odoo
from pytz import country_timezones

from odoo_cli.common import find_odoo_bin, get_version, settings
from odoo_cli.db import Environment, create_database, database_exists, drop_database
from odoo_cli.utils import get_odoo_args


@click.command("start")
@click.option("--init", is_flag=True, default=True, help="Initialize the database")
def run_start(init):
    """Start Odoo"""

    if init and not database_exists():
        create_database()

    args = get_odoo_args([])
    os.execvp(find_odoo_bin(), ["odoo-bin"] + args)


@click.command("init")
def init_database():
    """Init database"""

    if not database_exists():
        create_database()


@click.command("reset")
def reset_database():
    """Reset database"""

    if database_exists():
        drop_database()

    create_database()


@click.command("shell")
def run_shell():
    """Run Odoo Shell"""

    cmd = [find_odoo_bin(), "shell", "-d", "test", "--no-http"]
    os.execv(cmd[0], cmd)


@click.command("version")
def version():
    """Show Odoo version"""

    click.echo(get_version())


@click.command("update-language")
def update_language():
    """Update language"""

    with Environment() as env:
        lang = settings.lang
        country_code = settings.country_code

        odoo.tools.config["load_language"] = lang
        env.cr.commit()

        res_lang = (
            env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", lang)])
        )
        if res_lang:
            res_lang.active = True
            env.cr.commit()

        modules = env["ir.module.module"].search([("state", "=", "installed")])
        modules._update_translations(lang)

        country = env["res.country"].search([("code", "ilike", country_code)])[0]
        env["res.company"].browse(1).write(
            {
                "country_id": country_code and country.id,
                "currency_id": country_code and country.currency_id.id,
            }
        )
        if len(country_timezones.get(country_code, [])) == 1:
            users = env["res.users"].search([])
            users.write({"tz": country_timezones[country_code][0]})

        env.ref("base.user_admin").write({"lang": lang})
        env.cr.execute("SELECT login, password FROM res_users ORDER BY login")
        env.cr.commit()
