#!/usr/bin/env python
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import print_function

from distutils.sysconfig import get_python_lib
import imp
import os.path
from string import Template
import sys
from textwrap import dedent

from setuptools import (
    find_packages,
    setup,
    )
from setuptools.command.develop import develop
from setuptools.command.easy_install import ScriptWriter


class LPScriptWriter(ScriptWriter):
    """A modified ScriptWriter that uses Launchpad's boilerplate.

    Any script written using this class will set up its environment using
    `lp_sitecustomize` before calling its entry point.

    The standard setuptools handling of entry_points uses
    `pkg_resources.load_entry_point` to resolve requirements at run-time.
    This involves walking Launchpad's entire dependency graph, which is
    rather slow, and we always build all of our "optional" features anyway,
    so we might as well just take the simplified approach of importing the
    modules we need directly.  If we ever want to start using the "extras"
    feature of setuptools then we may want to revisit this.
    """

    template = Template(dedent("""
        import sys

        import ${module_name}

        if __name__ == '__main__':
            sys.exit(${module_name}.${attrs}())
        """))

    @classmethod
    def get_args(cls, dist, header=None):
        """See `ScriptWriter`."""
        if header is None:
            header = cls.get_header()
        for name, ep in dist.get_entry_map("console_scripts").items():
            cls._ensure_safe_name(name)
            script_text = cls.template.substitute({
                "attrs": ".".join(ep.attrs),
                "module_name": ep.module_name,
                })
            args = cls._get_script_args("console", name, header, script_text)
            for res in args:
                yield res


class lp_develop(develop):
    """A modified develop command to handle LP script generation."""

    def _get_orig_sitecustomize(self):
        env_top = os.path.join(os.path.dirname(__file__), "env")
        system_paths = [
            path for path in sys.path if not path.startswith(env_top)]
        try:
            fp, orig_sitecustomize_path, _ = (
                imp.find_module("sitecustomize", system_paths))
            if fp:
                fp.close()
        except ImportError:
            return ""
        if orig_sitecustomize_path.endswith(".py"):
            with open(orig_sitecustomize_path) as orig_sitecustomize_file:
                orig_sitecustomize = orig_sitecustomize_file.read()
                return dedent("""
                    # The following is from
                    # %s
                    """ % orig_sitecustomize_path) + orig_sitecustomize
        else:
            return ""

    def install_wrapper_scripts(self, dist):
        if not self.exclude_scripts:
            for args in LPScriptWriter.get_args(dist):
                self.write_script(*args)

            # Write bin/py for compatibility.  This is much like
            # env/bin/python, but if we just symlink to it and try to
            # execute it as bin/py then the virtualenv doesn't get
            # activated.  We use -S to avoid importing sitecustomize both
            # before and after the execve.
            py_header = LPScriptWriter.get_header("#!python -S")
            py_script_text = dedent("""\
                import os
                import sys

                os.execv(sys.executable, [sys.executable] + sys.argv[1:])
                """)
            self.write_script("py", py_header + py_script_text)

            env_top = os.path.join(os.path.dirname(__file__), "env")
            stdlib_dir = get_python_lib(standard_lib=True, prefix=env_top)
            orig_sitecustomize = self._get_orig_sitecustomize()
            sitecustomize_path = os.path.join(stdlib_dir, "sitecustomize.py")
            with open(sitecustomize_path, "w") as sitecustomize_file:
                sitecustomize_file.write(dedent("""\
                    import os
                    import sys

                    if "LP_DISABLE_SITECUSTOMIZE" not in os.environ:
                        if "lp_sitecustomize" not in sys.modules:
                            import lp_sitecustomize
                            lp_sitecustomize.main()
                    """))
                if orig_sitecustomize:
                    sitecustomize_file.write(orig_sitecustomize)

            # Write out the build-time value of LPCONFIG so that it can be
            # used by scripts as the default instance name.
            instance_name_path = os.path.join(env_top, "instance_name")
            with open(instance_name_path, "w") as instance_name_file:
                print(os.environ["LPCONFIG"], file=instance_name_file)

            # Write out the build-time Python major/minor version so that
            # scripts run with /usr/bin/python2 know whether they need to
            # re-exec.
            python_version_path = os.path.join(env_top, "python_version")
            with open(python_version_path, "w") as python_version_file:
                print("%s.%s" % sys.version_info[:2], file=python_version_file)


__version__ = '2.2.3'

setup(
    name='lp',
    version=__version__,
    packages=find_packages('lib'),
    package_dir={'': 'lib'},
    include_package_data=True,
    zip_safe=False,
    maintainer='Launchpad Developers',
    description=('A unique collaboration and Bazaar code hosting platform '
                 'for software projects.'),
    license='Affero GPL v3',
    # this list should only contain direct dependencies--things imported or
    # used in zcml.
    install_requires=[
        'ampoule',
        'backports.lzma; python_version < "3.3"',
        'beautifulsoup4[lxml]',
        'boto3',
        'breezy',
        'celery',
        'contextlib2; python_version < "3.3"',
        'cssselect',
        'cssutils',
        'defusedxml',
        'distro',
        'dkimpy[ed25519]',
        'dulwich',
        'feedparser',
        'fixtures',
        # Required for gunicorn[gthread].  We depend on it explicitly
        # because gunicorn declares its dependency in a way that produces
        # (and thus may cache) different wheels depending on whether it was
        # built on Python 2 or 3 while claiming that the wheels are
        # universal.
        # XXX cjwatson 2020-02-03: Remove this once we're on Python 3.
        'futures; python_version < "3.2"',
        'geoip2',
        'gunicorn',
        'importlib-resources; python_version < "3.7"',
        'ipaddress; python_version < "3.3"',
        'ipython',
        'jsautobuild',
        'launchpad-buildd',
        'launchpadlib',
        'lazr.batchnavigator',
        'lazr.config',
        'lazr.delegates',
        'lazr.enum',
        'lazr.jobrunner',
        'lazr.lifecycle',
        'lazr.restful',
        'lazr.sshserver',
        'lazr.uri',
        'lpjsmin',
        'Markdown',
        'meliae',
        'mock',
        'oauth',
        'oauthlib',
        'oops',
        'oops_amqp',
        'oops_datedir_repo',
        'oops_timeline',
        'oops_twisted',
        'oops_wsgi',
        'paramiko',
        'psutil',
        'pgbouncer',
        'psycopg2',
        'pyasn1',
        'pygettextpo',
        'pygpgme',
        'pyinotify',
        'pymacaroons',
        'pystache',
        'python-debian',
        'python-keystoneclient',
        'python-memcached',
        'python-mimeparse',
        'python-openid2',
        'python-subunit',
        'python-swiftclient',
        'pytz',
        'PyYAML',
        'rabbitfixture',
        'requests',
        'requests-file',
        'requests-toolbelt',
        'responses',
        'scandir',
        'secure-cookie',
        'setproctitle',
        'setuptools',
        'six',
        'soupmatchers',
        'Sphinx',
        'statsd',
        'storm',
        'talisker[gunicorn]',
        'tenacity',
        'testscenarios',
        'testtools',
        'timeline',
        'transaction',
        'treq',
        'Twisted[conch,tls]',
        'txfixtures',
        'txpkgupload',
        'virtualenv-tools3',
        'wadllib',
        'WebOb',
        'WebTest',
        'Werkzeug',
        'WSGIProxy2',
        'z3c.ptcompat',
        'zope.app.appsetup',
        'zope.app.http',
        'zope.app.publication',
        'zope.app.publisher',
        'zope.app.wsgi[testlayer]',
        'zope.authentication',
        'zope.browser',
        'zope.browsermenu',
        'zope.browserpage',
        'zope.browserresource',
        'zope.component[zcml]',
        'zope.configuration',
        'zope.contenttype',
        'zope.datetime',
        'zope.error',
        'zope.event',
        'zope.exceptions',
        'zope.formlib',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.location',
        'zope.login',
        'zope.pagetemplate',
        'zope.principalregistry',
        'zope.processlifetime',
        'zope.proxy',
        'zope.publisher',
        'zope.schema',
        'zope.security',
        'zope.securitypolicy',
        'zope.sendmail',
        'zope.session',
        'zope.tal',
        'zope.tales',
        'zope.testbrowser',
        'zope.testing',
        'zope.testrunner[subunit]',
        'zope.traversing',
        'zope.viewlet',  # only fixing a broken dependency
        'zope.vocabularyregistry',
        # Loggerhead dependencies. These should be removed once
        # bug 383360 is fixed and we include it as a source dist.
        'bleach',
        'Paste',
        'PasteDeploy',
        'SimpleTAL',
    ],
    url='https://launchpad.net/',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
    ],
    cmdclass={
        'develop': lp_develop,
    },
    entry_points=dict(
        console_scripts=[  # `console_scripts` is a magic name to setuptools
            'bingtestservice = '
                'lp.services.sitesearch.bingtestservice:main',
            'build-twisted-plugin-cache = '
                'lp.services.twistedsupport.plugincache:main',
            'generate-key-pair = '
                'lp.services.crypto.scripts.generatekeypair:main',
            'harness = lp.scripts.harness:python',
            'iharness = lp.scripts.harness:ipython',
            'ipy = IPython.frontend.terminal.ipapp:launch_new_instance',
            'jsbuild = lp.scripts.utilities.js.jsbuild:main',
            'kill-test-services = lp.scripts.utilities.killtestservices:main',
            'killservice = lp.scripts.utilities.killservice:main',
            'retest = lp.testing.utilities.retest:main',
            'run = lp.scripts.runlaunchpad:start_launchpad',
            'run-testapp = lp.scripts.runlaunchpad:start_testapp',
            'sprite-util = lp.scripts.utilities.spriteutil:main',
            'start_librarian = lp.scripts.runlaunchpad:start_librarian',
            'test = lp.scripts.utilities.test:main',
            'twistd = twisted.scripts.twistd:run',
            'version-info = lp.scripts.utilities.versioninfo:main',
            'watch_jsbuild = lp.scripts.utilities.js.watchjsbuild:main',
            'with-xvfb = lp.scripts.utilities.withxvfb:main',
        ]
    ),
)
