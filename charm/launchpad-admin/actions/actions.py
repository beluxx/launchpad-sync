#! /usr/bin/python3
# Copyright 2023 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import subprocess
import sys
import traceback
from pathlib import Path

sys.path.append("lib")

from charms.layer import basic  # noqa: E402

basic.bootstrap_charm_deps()
basic.init_config_states()

from charmhelpers.core import hookenv  # noqa: E402
from ols import base  # noqa: E402


def create_bot_account():
    params = hookenv.action_get()
    script = Path(base.code_dir(), "scripts", "create-bot-account.py")
    command = [
        "sudo",
        "-H",
        "-u",
        base.user(),
        "LPCONFIG=launchpad-admin",
        "--",
        script,
        "--username",
        params["username"],
    ]
    if "openid" in params:
        command.extend(["--openid", params["openid"]])
    if "email" in params:
        command.extend(["--email", params["email"]])
    if "sshkey" in params:
        command.extend(["--sshkey", params["sshkey"]])
    if "teams" in params:
        command.extend(["--teams", params["teams"]])
    subprocess.run(command, check=True)
    hookenv.action_set({"result": f"Created {params['username']}"})


def suspend_bot_account():
    params = hookenv.action_get()
    script = Path(base.code_dir(), "scripts", "suspend-bot-account.py")
    command = [
        "sudo",
        "-H",
        "-u",
        base.user(),
        "LPCONFIG=launchpad-admin",
        "--",
        script,
        "--email",
        params["email"],
    ]
    subprocess.run(command, check=True)
    hookenv.action_set({"result": f"Suspended {params['email']}"})


def main(argv):
    action = Path(argv[0]).name
    try:
        if action == "create-bot-account":
            create_bot_account()
        elif action == "suspend-bot-account":
            suspend_bot_account()
        else:
            hookenv.action_fail(f"Action {action} not implemented.")
    except Exception:
        hookenv.action_fail("Unhandled exception")
        tb = traceback.format_exc()
        hookenv.action_set(dict(traceback=tb))
        hookenv.log(f"Unhandled exception in action {action}:")
        for line in tb.splitlines():
            hookenv.log(line)


if __name__ == "__main__":
    main(sys.argv)
