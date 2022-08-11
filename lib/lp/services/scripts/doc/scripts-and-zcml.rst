Scripts and ZCML
----------------

The full Zope component architecture is available from scripts so long
as they call `execute_zcml_for_scripts()`.

Let's make a simple example script that uses getUtility and the database
to demonstrate this:

    >>> import os
    >>> import subprocess
    >>> import tempfile
    >>> from textwrap import dedent
    >>> script_file = tempfile.NamedTemporaryFile(mode='w')
    >>> _ = script_file.write(dedent("""\
    ...     from lp.services.scripts import execute_zcml_for_scripts
    ...     from lp.registry.interfaces.person import IPersonSet
    ...     from zope.component import getUtility
    ... 
    ...     execute_zcml_for_scripts()
    ...     print(getUtility(IPersonSet).get(1).displayname)
    ...     """))
    >>> script_file.flush()

Run the script (making sure it uses the testrunner configuration).

    >>> from lp.services.config import config
    >>> bin_py = os.path.join(config.root, 'bin', 'py')
    >>> proc = subprocess.Popen(
    ...     [bin_py, script_file.name], stdout=subprocess.PIPE, stderr=None,
    ...     universal_newlines=True)

Check that we get the expected output.

    >>> print(proc.stdout.read())
    Mark Shuttleworth

    >>> print(proc.wait())
    0

Remove the temporary file.

    >>> script_file.close()
