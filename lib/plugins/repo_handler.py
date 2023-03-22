"""
MIT License

Copyright (C) 2023 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

import logging
import json
import importlib
import importlib.resources
import urllib

import lib.common.exceptions as exceptions
import lib.common.utils as utils
from lib.db.db_plugins import DBPlugins
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except

CABERNET_REPO = 'manifest.json'


class RepoHandler:

    logger = None

    def __init__(self, _config_obj):
        self.config_obj = _config_obj
        if RepoHandler.logger is None:
            RepoHandler.logger = logging.getLogger(__name__)
        self.plugin_db = DBPlugins(_config_obj.data)



    def load_cabernet_repo(self):
        """
        Loads the manifest which points to the plugin.json list of plugins
        Will update the database on the manifest and plugin list
        If there is a plugin that is no longer in the list, will tag for
        deletion. (don't know at this point if it is installed.)
        """
        repo_settings = self.import_cabernet_manifest()
        self.save_repo(repo_settings)
        self.update_plugins(repo_settings)

    def import_cabernet_manifest(self):
        """
        Loads the manifest for cabernet repo
        """
        json_settings = importlib.resources.read_text(self.config_obj.data['paths']['resources_pkg'], CABERNET_REPO)
        settings = json.loads(json_settings)
        if settings:
            settings = settings['plugin']
            settings['repo_url'] = CABERNET_REPO
        return settings

    def save_repo(self, _repo):
        """
        Saves to DB the repo json settings
        """
        self.plugin_db.save_repo(_repo)


    def update_plugins(self, _repo_settings):
        """
        Gets the list of plugins for this repo from [dir][info] and updates the db
        """
        uri = _repo_settings['dir']['info']
        plugin_json = self.get_uri_json_data(uri)
        if plugin_json:
            plugin_json = plugin_json['plugins']
            for plugin in plugin_json:
                plugin = plugin['plugin']
                if 'repository' in plugin['category']:
                    continue
                # pull the db item. merge them and then update the db with new data.
                plugin_data = self.plugin_db.get_plugins(_installed=None, _repo=_repo_settings['id'], _plugin_id=plugin['id'])
                if plugin_data:
                    plugin_data = plugin_data[0]
                    plugin['repoid'] = _repo_settings['id']
                    plugin['version']['installed'] = plugin_data['version']['installed']
                    plugin['version']['latest'] = plugin['version']['current']
                    plugin['version']['current'] = plugin_data['version']['current']
                    plugin['external'] = plugin_data['external']
                else:
                    plugin['repoid'] = _repo_settings['id']
                    plugin['version']['installed'] = False
                    plugin['version']['latest'] = plugin['version']['current']
                    plugin['version']['current'] = None
                self.plugin_db.save_plugin(plugin)


    @handle_url_except()
    @handle_json_except
    def get_uri_json_data(self, _uri):
        header = {
            'Content-Type': 'application/json',
            'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.load(resp)