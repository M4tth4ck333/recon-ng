#!/usr/bin/env python3
"""
recon-ng/recon/core/farmework.py
m4tth4ck
Original leet.py by Tim Tomes (LaNMaSteR53)
Enhanced wrapper by: Enhanced Development Team
"""
from pathlib import Path
import re
import sys
import uuid
import os
import json

from recon.core import framework

class Recon(framework.Framework):

    repo_url = 'https://raw.githubusercontent.com/lanmaster53/recon-ng-modules/master/'

    def __init__(self, check=True, analytics=True, marketplace=True, accessible=False):
        super().__init__('base')
        self._name = 'recon-ng'
        self._prompt_template = '{}[{}] > '
        self._base_prompt = self._prompt_template.format('', self._name)

        # Flags
        self._check = check
        self._analytics = analytics
        self._marketplace = marketplace
        self._accessible = accessible

        # Pfade als Klassenvariablen
        self.app_path = framework.Framework.app_path = Path(sys.path[0])
        self.core_path = framework.Framework.core_path = self.app_path / 'core'
        self.home_path = framework.Framework.home_path = Path.home() / '.recon-ng'
        self.mod_path = framework.Framework.mod_path = self.home_path / 'modules'
        self.data_path = framework.Framework.data_path = self.home_path / 'data'
        self.spaces_path = framework.Framework.spaces_path = self.home_path / 'workspaces'

    def start(self, mode, workspace='default'):
        self._mode = framework.Framework._mode = mode
        self._init_global_options()
        self._init_home()
        self._init_workspace(workspace)
        self._check_version()

        if self._mode == Mode.CONSOLE:
            self._print_banner()
            self.cmdloop()

    def _init_global_options(self):
        self.options = self._global_options
        self.register_option('nameserver', '8.8.8.8', True, 'default nameserver for the resolver mixin')
        self.register_option('proxy', None, False, 'proxy server (address:port)')
        self.register_option('threads', 10, True, 'number of threads (where applicable)')
        self.register_option('timeout', 10, True, 'socket timeout (seconds)')
        self.register_option('user-agent', f"Recon-ng/v{__version__.split('.')[0]}", True, 'user-agent string')
        self.register_option('verbosity', 1, True, 'verbosity level (0 = minimal, 1 = verbose, 2 = debug)')

    def _init_home(self):
        self.home_path.mkdir(parents=True, exist_ok=True)
        self._query_keys('CREATE TABLE IF NOT EXISTS keys (name TEXT PRIMARY KEY, value TEXT)')
        self._fetch_module_index()

    def _check_version(self):
        if not self._check:
            self.alert('Version check disabled.')
            return

        try:
            version_url = 'https://raw.githubusercontent.com/lanmaster53/recon-ng/master/VERSION'
            content = self.request('GET', version_url).text
            remote = re.search(r"'(\d+\.\d+\.\d+[^']*)'", content).group(1)
        except Exception as e:
            self.error(f"Version check failed ({type(e).__name__}).")
            return

        if remote != __version__:
            self.alert('Your version of Recon-ng does not match the latest release.')
            self.alert('Please consider updating before further use.')
            self.output(f"Remote version:  {remote}")
            self.output(f"Local version:   {__version__}")

    def _print_banner(self):
        banner = BANNER_SMALL if self._accessible else BANNER
        author_info = (
            f"{framework.Colors.O}{self._name}, version {__version__}, by {__author__}{framework.Colors.N}"
            if self._accessible
            else f"{framework.Colors.O}[{self._name} v{__version__}, {__author__}]{framework.Colors.N}".center(len(max(banner.splitlines(), key=len)) + 8)
        )
        print(banner)
        print(author_info)
        print('')

        counts = [(len(self._loaded_category[x]), x) for x in self._loaded_category]
        if counts:
            max_len = max(len(str(count[0])) for count in counts)
            for count in sorted(counts, reverse=True):
                cnt = f"[{count[0]}]".ljust(max_len + 2)
                print(f"{framework.Colors.B}{cnt} {count[1].title()} modules{framework.Colors.N}")
                setattr(self, f"do_{count[0]}", self._menu_egg)
        else:
            self.alert('No modules enabled/installed.')
        print()

    def _send_analytics(self, cd):
        if not self._analytics:
            self.debug('Analytics disabled.')
            return

        try:
            cid_file = self.home_path / '.cid'
            if not cid_file.exists():
                cid_file.write_text(str(uuid.uuid4()), encoding='utf-8')

            cid = cid_file.read_text(encoding='utf-8').strip()
            params = {
                'v': 1,
                'tid': 'UA-52269615-2',
                'cid': cid,
                't': 'screenview',
                'an': 'Recon-ng',
                'av': __version__,
                'cd': cd,
            }
            self.request('GET', 'https://www.google-analytics.com/collect', params=params)
        except Exception as e:
            self.debug(f"Analytics failed ({type(e).__name__}).")
