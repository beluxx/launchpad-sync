# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for running external commands."""

__all__ = [
    'run_command',
    'run_script',
    ]

import subprocess
import sys


def run_command(command, args=None, input=None, universal_newlines=True):
    """Run an external command in a separate process.

    :param command: executable to run.
    :param args: optional list of command-line arguments.
    :param input: optional text to feed to command's standard input.
    :param universal_newlines: passed to `subprocess.Popen`, defaulting to
        True.
    :return: tuple of return value, standard output, and standard error.
    """
    command_line = [command]
    if args:
        command_line.extend(args)
    if input is not None:
        stdin = subprocess.PIPE
    else:
        stdin = None

    child = subprocess.Popen(
        command_line, stdin=stdin, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=universal_newlines)
    stdout, stderr = child.communicate(input)
    result = child.wait()
    return (result, stdout, stderr)


def run_script(script, args=None, input=None, universal_newlines=True):
    """Run a Python script in a child process, using current interpreter.

    :param script: Python script to run.
    :param args: optional list of command-line arguments.
    :param input: optional string to feed to standard input.
    :param universal_newlines: passed to `subprocess.Popen`, defaulting to
        True.
    :return: tuple of return value, standard output, and standard error.
    """
    interpreter_args = [script]
    if args:
        interpreter_args.extend(args)

    return run_command(
        sys.executable, interpreter_args, input,
        universal_newlines=universal_newlines)
