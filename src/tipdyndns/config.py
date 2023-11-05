"""config.py"""
from typing import List, Any

import os
import logging

# from sqlalchemy.engine.url import make_url


import munch
import benedict
import json

import yaml


from rich import print as rprint

from appdirs import (
    user_config_dir,
    site_config_dir,
    # site_log_dir, --> doesn't exist?
    user_log_dir,
    user_data_dir,
    site_data_dir,
)

FILENAME = 'config.yaml'

DEFAULT_SETTINGS = {
    # 'description': "tipdyndns's defaults",
    # 'type': 'default',
    'logging': {
        'level': 'DEBUG',
        'filename': 'default.log',
        'use_console': True,
        'backup_count': 5,
        'max_size': 1024,
        # format for logfile. this does not affect console.
        'format': '%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s',
        'datefmt': '%d-%m-%Y %H:%M:%S',
    },
    # 'database': {
    #     'username': None,
    #     'password': None,
    #     'protocol': None,
    #     'host': None,
    #     'database': None
    # },
 }


class ConfigNotFoundError(Exception):
    """Raised when configuration could not be found."""

    def __init__(self, filename, search_path, message="Config file could not be found."):
            self.filename = filename
            self.search_path = search_path
            self.message = message
            super().__init__(self.message)



class Configuration(object):
    """..."""

    def __init__(self, app, user_mode=True, settings=DEFAULT_SETTINGS, filename=None):
        """Create a new Configuration instance."""
        self.app = app
        self.user_mode = user_mode
        self.settings = munch.Munch.fromDict(settings)
        self.author = ''
        self.filename = filename

    def __rich_repr__(self):
        """Pretty printing for rich."""
        yield 'app', self.app
        yield 'user_mode', self.user_mode
        yield 'filename', self.filename
        yield 'settings', self.settings.toDict()

    @property
    def log_dir(self):
        if self.user_mode:
            return user_log_dir(self.app, self.author)

        return site_data_dir(self.app, self.author)

    @property
    def config_dir(self):
        if self.user_mode:
            return user_config_dir(self.app, self.author)

        return site_config_dir(self.app, self.author)

    @property
    def data_dir(self):
        if self.user_mode:
            return user_data_dir(self.app, self.author)

        return site_data_dir(self.app, self.author)

    # @property
    # def database_URI(self):
    #     """Return `self.settings.database.uri` as URI."""
    #     URI = self.settings.database.uri
    #     return make_url(URI)

    def update(self, config_file: str = None, silent=False):
        """Update initial settings from file.

            config_file overrides self.filename is specified.
        """
        if (config_file is None):
            if self.filename is None:
                try:
                    config_file = self.find_config_file()
                except ConfigNotFoundError as e:
                    if not silent:
                        rprint(f"[orange3]WARNING:[/] Could not find [b]{e.filename}[/b] in {e.search_path}")
                        rprint(f"[orange3]WARNING:[/] using defaults.")
            else:
                config_file = self.filename

        if config_file is not None:
            self.load(config_file)

    def find_config_file(self) -> str:
        """Attempt to find a configuration file."""
        app = self.app
        author = self.author

        # Determine search path if not explicitly provided.
        search_paths = [self.config_dir]

        if not self.user_mode:
            search_paths.extend([
                f'/etc/{app}',
            ])

        # The search begins ...
        for location in search_paths:
            fullpath = os.path.join(location, FILENAME)
            # print(fullpath)

            if os.path.exists(fullpath):
                # print(f'found path: {fullpath}')
                return fullpath

        m = f'Could not find a suitable configuration file in {search_paths}.'
        raise ConfigNotFoundError(FILENAME, search_paths)

    def load(self, filename: str):
        """Load a configuration file.

        Args:
            filename (str): absolute or relative path to config file.
        """
        log = logging.getLogger('config')
        log.info(f'Loading configuration from "{filename}"')

        with open(filename) as fp:
            config = yaml.load(fp.read(), Loader=yaml.SafeLoader)

        # Do a deep-merge of the current and read configuration.
        # For some reason Munch.fromDict chokes on benedict,
        # so we'll jump through a few hoops.
        current = self.settings.toDict()
        bcurrent = benedict.benedict(current)
        bcurrent.merge(config, overwrite=True)
        merged = json.loads(bcurrent.to_json())
        self.settings = munch.Munch.fromDict(merged)
        self.filename = filename

    def save(self, filename: str = None):
        """Save configuration to disk."""
        filename = filename or self.filename

        log = logging.getLogger('config')
        log.info(f'Writing configuration to "{filename}"')

        with open(filename, 'w') as fp:
            yaml.dump(
                self.settings,
                fp,
                Dumper=yaml.SafeDumper,
            )

