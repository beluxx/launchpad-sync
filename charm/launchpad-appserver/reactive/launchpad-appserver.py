# Copyright 2022 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import subprocess
from multiprocessing import cpu_count

from charmhelpers.core import hookenv, host, templating
from charms.launchpad.base import (
    config_file_path,
    configure_lazr,
    get_service_config,
    lazr_config_files,
    strip_dsn_authentication,
    update_pgpass,
)
from charms.reactive import (
    clear_flag,
    helpers,
    set_flag,
    set_state,
    when,
    when_not,
)
from ols import base, postgres
from psycopg2.extensions import parse_dsn


def reload_or_restart(service):
    subprocess.run(["systemctl", "reload-or-restart", service], check=True)


def enable_service(service):
    subprocess.run(["systemctl", "enable", service], check=True)


@host.restart_on_change(
    {
        "/etc/rsyslog.d/22-launchpad.conf": ["rsyslog"],
        "/lib/systemd/system/launchpad.service": ["launchpad"],
        config_file_path("launchpad-appserver/gunicorn.conf.py"): [
            "launchpad"
        ],
    },
    restart_functions={
        "rsyslog": reload_or_restart,
        "gunicorn": enable_service,
    },
)
def configure_gunicorn(config):
    hookenv.log("Writing gunicorn configuration.")
    config = dict(config)
    if config["wsgi_workers"] == 0:
        config["wsgi_workers"] = cpu_count() * 2 + 1
    templating.render(
        "gunicorn.conf.py.j2",
        config_file_path("launchpad-appserver/gunicorn.conf.py"),
        config,
    )
    templating.render(
        "launchpad.service.j2", "/lib/systemd/system/launchpad.service", config
    )
    host.add_user_to_group("syslog", base.user())
    templating.render("rsyslog.j2", "/etc/rsyslog.d/22-launchpad.conf", config)


def configure_logrotate(config):
    hookenv.log("Writing logrotate configuration.")
    templating.render(
        "logrotate.conf.j2",
        "/etc/logrotate.d/launchpad",
        config,
        perms=0o644,
    )


def restart(soft=False):
    if soft:
        reload_or_restart("launchpad")
    else:
        host.service_restart("launchpad")


def config_files():
    files = []
    files.extend(lazr_config_files())
    files.append(config_file_path("launchpad-appserver/launchpad-lazr.conf"))
    files.append(
        config_file_path("launchpad-appserver-secrets-lazr.conf", secret=True)
    )
    return files


@when(
    "launchpad.base.configured",
    "session-db.master.available",
    "memcache.available",
)
@when_not("service.configured")
def configure(session_db, memcache):
    config = get_service_config()
    session_db_primary, _ = postgres.get_db_uris(session_db)
    # XXX cjwatson 2022-09-23: Mangle the connection string into a form
    # Launchpad understands.  In the long term it would be better to have
    # Launchpad be able to consume unmodified connection strings.
    update_pgpass(session_db_primary)
    config["db_session"] = strip_dsn_authentication(session_db_primary)
    config["db_session_user"] = parse_dsn(session_db_primary)["user"]
    config["memcache_servers"] = ",".join(
        sorted(
            f"({host}:{port},1)"
            for host, port in memcache.memcache_hosts_ports()
        )
    )
    configure_lazr(
        config,
        "launchpad-appserver-lazr.conf",
        "launchpad-appserver/launchpad-lazr.conf",
    )
    configure_lazr(
        config,
        "launchpad-appserver-secrets-lazr.conf",
        "launchpad-appserver-secrets-lazr.conf",
        secret=True,
    )
    configure_gunicorn(config)
    configure_logrotate(config)

    restart_type = None
    if helpers.any_file_changed(
        [base.version_info_path(), "/lib/systemd/system/launchpad.service"]
    ):
        restart_type = "hard"
    elif helpers.any_file_changed(config_files()):
        restart_type = "soft"
    if restart_type is None:
        hookenv.log("Not restarting, since no config files were changed")
    else:
        hookenv.log(f"Config files changed; performing {restart_type} restart")
        restart(soft=(restart_type == "soft"))

    set_state("service.configured")


@when("service.configured")
def check_is_running():
    hookenv.status_set("active", "Ready")


@when("nrpe-external-master.available", "service.configured")
@when_not("launchpad.appserver.nrpe-external-master.published")
def nrpe_available(nrpe):
    config = hookenv.config()
    healthy_regex = (
        r"(\/\+icing\/rev[0-9a-f]+\/).*(Is your project registered yet\?)"
    )
    nrpe.add_check(
        [
            "/usr/lib/nagios/plugins/check_http",
            "-H",
            "localhost",
            "-p",
            str(config["port_main"]),
            "-l",
            "--regex=%s" % healthy_regex,
        ],
        name="check_launchpad_appserver",
        description="Launchpad appserver",
        context=config["nagios_context"],
    )
    set_flag("launchpad.appserver.nrpe-external-master.published")


@when("launchpad.appserver.nrpe-external-master.published")
@when_not("nrpe-external-master.available")
def nrpe_unavailable():
    clear_flag("launchpad.appserver.nrpe-external-master.published")
