import sys

import click
import odoo
from odoo.cli.server import main as odoo_main
from odoo.cli.server import report_configuration
from odoo.cli.shell import Shell
from pytz import country_timezones

from odoo_cli.common import get_version
from odoo_cli.db import Environment, create_database, database_exists, drop_database
from odoo_cli.utils import (
    fix_addons_path,
    get_odoo_args,
    random_password,
    restart_process,
    settings,
    wait_for_psql,
)

ODOO_LOG_LEVELS = [
    "info",
    "debug_rpc",
    "warn",
    "test",
    "critical",
    "runbot",
    "debug_sql",
    "error",
    "debug",
    "debug_rpc_answer",
    "notset",
]


@click.command("start")
@click.option("--dev", is_flag=True, help="Run Odoo in development mode")
@click.option("--force-db", is_flag=True, help="Force database creation")
@click.option("--unsafe", is_flag=True, help="Run Odoo in unsafe mode")
@click.option(
    "--log-level",
    default="info",
    help="Set the log level",
    type=click.Choice(ODOO_LOG_LEVELS, case_sensitive=False),
)
def run_start(dev: bool, force_db: bool, unsafe: bool, log_level: str):
    """Start Odoo"""

    wait_for_psql()

    args = get_odoo_args(
        [f"--log-level={log_level}"], database=False, dev=dev, safe=not unsafe
    )

    odoo.tools.config.parse_config(args)
    odoo.tools.config["addons_path"] = fix_addons_path()
    odoo.tools.config["db_name"] = False
    odoo.tools.config.save()

    # os.execvp(find_odoo_bin(), ["odoo-bin"])

    if dev:
        args.extend(["--dev=reload"])

    if force_db:
        args.extend(["--database", settings.db_name])

    odoo_main(args)


@click.command("reload-conf")
def reload_configuration():
    """Reload Odoo configuration from environment variables"""

    args = get_odoo_args([], database=False)
    odoo.tools.config.parse_config(args)
    odoo.tools.config["addons_path"] = fix_addons_path()
    odoo.tools.config["db_name"] = False
    odoo.tools.config.save()

    report_configuration()


@click.command("init")
def init_database():
    """Init database"""

    wait_for_psql()

    if not database_exists():
        create_database()


@click.command("reset")
def reset_database():
    """Reset database"""

    if database_exists():
        drop_database()

    create_database()


@click.command("drop")
def run_drop_database():
    """Drop database"""

    if database_exists():
        drop_database()


@click.command("shell")
def run_shell():
    """Run Odoo Shell"""

    # args = get_odoo_args(["shell", "--no-http"])
    # os.execvp(find_odoo_bin(), ["odoo-bin"] + args)
    # # cmd = [find_odoo_bin(), "shell", "-d", settings.db_name, "--no-http"]
    # # os.execv(cmd[0], cmd)

    args = get_odoo_args(["--no-http"], database=True)
    Shell().run(args)


@click.command("restart")
@click.option("--force", is_flag=True, help="Force PID")
def restart(force: bool):
    """Restart Odoo"""

    try:
        restart_process(force=force)
    except Exception as error:
        click.echo(error)
        sys.exit(1)


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


@click.command("regenerate-assets")
def regenerate_assets():
    """Regenerate assets"""
    with Environment() as env:
        domain = [
            "&",
            ["res_model", "=", "ir.ui.view"],
            "|",
            ["name", "=like", "%.assets_%.css"],
            ["name", "=like", "%.assets_%.js"],
        ]
        res = env["ir.attachment"].search(domain)

        if res:
            click.echo(f"Assets found ({len(res)}): {', '.join(res.mapped('name'))}")
            res.unlink()
            env.cr.commit()


@click.command("reset-master-password")
def reset_master_password():
    """Reset master password"""

    new_password = random_password()
    odoo.tools.config["admin_passwd"] = new_password
    odoo.tools.config.save()

    click.echo(f"New master password: {new_password}")

    report_configuration()
