
import odoo



def set_language(lang, country):
    from pytz import country_timezones

    lang = "fr_FR"
    country_code = "fr"

    # odoo.tools.config['load_language'] = lang
    # env.cr.commit()

    # res_lang = env['res.lang'].with_context(active_test=False).search([('code', '=', lang)])
    # res_lang.active = True
    # env.cr.commit()

    # modules = env['ir.module.module'].search([('state', '=', 'installed')])
    # modules._update_translations(lang)

    # country = env['res.country'].search([('code', 'ilike', country_code)])[0]
    # env['res.company'].browse(1).write({'country_id': country_code and country.id, 'currency_id': country_code and country.currency_id.id})
    # if len(country_timezones.get(country_code, [])) == 1:
    #     users = env['res.users'].search([])
    #     users.write({'tz': country_timezones[country_code][0]})

    # env.ref('base.user_admin').write({'lang': lang})
    # env.cr.execute('SELECT login, password FROM res_users ORDER BY login')
    # env.cr.commit()    
    
    
#!/usr/bin/env python3
"""
Odoo.sh Import Database

This script replaces the current database + filestore with the provided backup.
It supports backups downloaded from your Odoo's database manager (.zip format)

WARNING: This script will erase the existing database content!


Usage:
  odoosh-import-database [--help] [--logfile=FILE] <backup_file>

Options:
  -h, --help             Show this screen and exit.
  -f, --logfile=FILE     Store output into the specified log file
"""
import json
import logging
import os
import psycopg2
import shutil
import subprocess
import sys
import tempfile

from os.path import join as opj

import docopt


class InvalidDumpError(Exception):
    pass


def run(dump):
    returncode = 0
    temp_dir = False
    try:
        db_name = os.environ.get('PGDATABASE')
        db_user = os.environ.get('PGUSER')
        if not db_name or not db_user:
            raise Exception("PGDATABASE or PGUSER not in environ")

        temp_dir = tempfile.mkdtemp(dir='/home/odoo')
        unzip_dump(dump, temp_dir)
        sql_dump, filestore = get_dump_paths(temp_dir)

        with psycopg2.connect('') as conn:
            with conn.cursor() as cr:
                base_version = get_base_version(cr)
                empty_database(cr, db_user)

        restore_database(sql_dump)
        handle_filestore(filestore, db_name, base_version)

    except InvalidDumpError as e:
        logging.error(str(e) or "Unexpected Error.")
        returncode = 2
    except Exception as e:
        logging.error(str(e) or "Unexpected Error.")
        returncode = 1
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir)
        return returncode


def unzip_dump(dump, temp_dir):
    logging.info("Unzipping %s...", dump)
    cmd = ['unzip', dump, '-d', temp_dir]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if stderr:
        raise Exception("Error while performing unzip on '%s'" % dump)


def get_dump_paths(temp_dir):
    sql_dump = opj(temp_dir, 'dump.sql')
    filestore = opj(temp_dir, 'filestore')
    if not os.path.exists(sql_dump) or not os.path.exists(filestore):
        for path in os.listdir(temp_dir):
            if path.endswith('.json'):
                with open(opj(temp_dir, path), 'r') as f:
                    json_info = json.loads(f.read())
                    if isinstance(json_info, dict):
                        bak_dir = opj(temp_dir, path)[:-len('.json')]
                        filestore = opj(bak_dir, 'home/odoo/data/filestore', json_info.get('name', ''))
                        sql_dump = bak_dir + '.sql'
                        sql_gz_dump = sql_dump + '.gz'
                        if os.path.exists(filestore) and os.path.exists(sql_gz_dump):
                            cmd = ['gunzip', sql_gz_dump]
                            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            stdout, stderr = proc.communicate()
                            if stderr:
                                raise InvalidDumpError("Error while gunzipping the sql.gz dump")
                            break
        if not os.path.exists(sql_dump) or not os.path.exists(filestore):
            raise InvalidDumpError("File of incorrect format, missing sql dump or filestore, please make sure "
                                   "to either use the /web/database/manager or the Odoo.sh plain backup format.")
    return sql_dump, filestore


def get_base_version(cr):
    base_version = False
    try:
        cr.execute("SELECT latest_version FROM ir_module_module WHERE name = 'base'")
        result = cr.fetchall()
        if len(result):
            base_version = result[0][0]
    except psycopg2.ProgrammingError:
        logging.warning("Could not verify which version is installed to determine if filestores should be "
                        "merged or not, replacing filestore by default")
        cr.connection.rollback()
    return base_version


def empty_database(cr, db_user):
    logging.info("Emptying database...")
    try:
        cr.execute("""
            DO $$
                DECLARE
                    command text;
                BEGIN
                   FOR command IN (select concat('drop table if exists "', tablename, '" cascade;') from pg_tables WHERE schemaname = 'public') LOOP
                      EXECUTE command;
                   END LOOP;
                   FOR command IN (select concat('drop sequence "', c.relname, '";') FROM pg_class c WHERE (c.relkind = 'S')) LOOP
                      EXECUTE command;
                   END LOOP;
                END;
            $$;
        """)  # NOQA
    except psycopg2.ProgrammingError as e:
        logging.warning('Errors while emptying database:\n%s', str(e))
        cr.execute("""SELECT count(*)
                      FROM pg_tables
                      WHERE tableowner = %s""", (db_user, ))
        count = cr.fetchall()
        if not len(count) or count[0][0] != 0:
            raise Exception("Some tables could not be dropped.")


def restore_database(sql_dump):
    logging.info("Restoring database from dump...")
    cmd = ['psql', '-f', sql_dump]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if stderr:
        errors = [line for line in stderr.decode('utf8').splitlines()
                  if not line.endswith("must be owner of extension unaccent")]
        if errors:
            logging.warning("Errors while restoring sql dump, stderr:\n%s", '\n'.join(errors))


def handle_filestore(filestore, db_name, base_version):
    if os.listdir(filestore):
        with psycopg2.connect('') as conn:
            with conn.cursor() as cr:
                merge_filestores = False
                try:
                    cr.execute("SELECT latest_version FROM ir_module_module WHERE name = 'base'")
                    result = cr.fetchall()
                    if len(result) and base_version and not base_version.startswith(result[0][0][:3]):
                        merge_filestores = True
                except Exception:
                    logging.warning("Could not verify which version is installed to determine if filestores "
                                    "should be merged or not, replacing filestore by default")

        logging.info("%s filestore...", 'Merging' if merge_filestores else 'Replacing')
        container_filestore = opj('/home/odoo/data/filestore', db_name)
        if merge_filestores:
            cmd = ['rsync', '-a', filestore + os.path.sep, container_filestore]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if stderr:
                raise Exception("Error while merging filestores with: %s" % ' '.join(cmd))
        else:
            shutil.rmtree(container_filestore)
            shutil.move(filestore, container_filestore)
    else:
        logging.info('Imported filestore is empty, leaving current one')


def main():
    argv = sys.argv[1:] or ['-h']
    args = docopt.docopt(__doc__, argv=argv)

    # Set up logger
    logging_kwargs = {
        'format': '%(asctime)s %(levelname)s: %(message)s',
        'level': logging.INFO,
    }
    if args['--logfile']:
        logging_kwargs['filename'] = args['--logfile']
    logging.basicConfig(**logging_kwargs)

    logging.info('Started.')
    returncode = run(args['<backup_file>'])
    logging.info('Finished with error(s).' if returncode else 'Finished.')
    sys.exit(returncode)


if __name__ == '__main__':
    main()
    