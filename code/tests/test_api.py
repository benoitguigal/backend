#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
from unittest import TestCase

from ..api import app
from .. import config


app.testing = True
config.init()
config.read_conf()


class ApiTestBase(TestCase):

    def setUp(self):
        app.testing = True
        self.test_client = app.test_client()


class ConfTest(ApiTestBase):

    def test_get(self):
        """ it should retrieve the configuration """
        response = self.test_client.get("/conf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        data = json.loads(response.get_data())
        expected_keys = ["paths", "threads_by_job", "data_extensions", "write_queue_length", "test_chunk_size",
                         "api", "recipe_extensions", "machine_learning", "validation", "projects", "log"]
        for expected_key in expected_keys:
            self.assertIn(expected_key, data.keys())




