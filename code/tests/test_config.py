#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from unittest import TestCase
from .. import config
from ..config import read_conf_dir, deepupdate


class ConfigTestCase(TestCase):

    def test_init(self):
        """ it should initializes global conf variables """
        global_vars = ["manager", "jobs", "inmemory", "log", "levCache", "jobs_list"]
        for global_var in global_vars:
            self.assertNotIn(global_var, vars(config).keys())
        config.init()
        for global_var in global_vars:
            self.assertIn(global_var, vars(config).keys())

    def test_read_config_dir(self):
        """ it should read the conf directory """
        conf_dir = "conf"
        cfg = {"global": {"projects": {}}}
        cfg = read_conf_dir(conf_dir, cfg)
        expected_config_keys = [
            'recipes',
            'datasets',
            'connectors',
            'global']
        self.assertEqual(cfg.keys(), expected_config_keys)
        expected_global_config_keys = [
            'paths',
            'validation',
            'api',
            'threads_by_job',
            'write_queue_length',
            'test_chunk_size',
            'recipe_extensions',
            'data_extensions',
            'machine_learning',
            'log',
            'projects']
        self.assertEqual(cfg['global'].keys(), expected_global_config_keys)

    def test_deep_update(self):
        """ it should deep update a dictionary """
        original = {
            "key_1": "original_value_1",
            "key_2": {
                "key_21": "original_value_21"
            },
            "key_3": "original_value_3"
        }

        update = {
            "key_2": {
                "key_21": "update_value_21",
                "key_22": "update_value_22"
            },
            "key_3": "update_value_3",
            "key_4": "update_value_4"
        }

        updated = deepupdate(original, update)

        expected = {
            'key_1': 'original_value_1',
            'key_2': {
                'key_21': 'update_value_21',
                'key_22': 'update_value_22'
            },
            'key_3': 'update_value_3',
            'key_4': 'update_value_4'
        }

        self.assertEqual(updated, expected)



