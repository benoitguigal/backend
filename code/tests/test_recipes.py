#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from unittest import TestCase
import tempfile
from os import path
import shutil

import pandas as pd

from ..recipes import fwf_format, to_fwf, Connector, Dataset
from .. import config


class UtilsTestCase(TestCase):

    def test_fwf_format(self):
        """ it should convert a pandas row to a fixed length string """
        data = [
            ["John", "Doe", "1956/01/03", "Connecticut"],
        ]
        columns = ["fist_name", "last_name", "date_of_birth", "state"]
        df = pd.DataFrame(data, columns=columns)
        row = df.iloc[0]
        widths = [15, 15, 15, 15]
        row_formatted = fwf_format(row, widths)
        expected = "John           Doe            1956/01/03     Connecticut    "
        self.assertEqual(row_formatted, expected)

    def test_to_fwf(self):
        data = [
            ["John", "Doe", "1956/01/03", "Connecticut"],
            ["Bob", "Smith", "1967/05/26", "Ohio"]

        ]
        columns = ["fist_name", "last_name", "date_of_birth", "state"]
        df = pd.DataFrame(data, columns=columns)
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            widths = [15, 15, 15, 15]
            to_fwf(df, tmp.name, widths=widths, names=columns)
            with open(tmp.name, 'r') as tmp:
                lines = tmp.read().splitlines()
                expected = [
                    "John           Doe            1956/01/03     Connecticut    ",
                    "Bob            Smith          1967/05/26     Ohio           "
                ]
                self.assertEqual(lines, expected)


class UploadConnectorTestCase(TestCase):

    def setUp(self):
        config.init()
        config.read_conf()

    def test_init(self):
        connector = Connector(name="upload")
        upload_connector_conf = config.conf["connectors"]["upload"]
        self.assertEqual(connector.type, upload_connector_conf["type"])  # default=filesystem
        self.assertEqual(connector.database, upload_connector_conf["database"])  # default=upload


class ElasticSearchConnectorTestCase(TestCase):

    def setUp(self):
        config.init()
        config.read_conf()

    def test_init(self):
        connector = Connector(name="elasticsearch")
        es_connector_conf = config.conf["connectors"]["elasticsearch"]
        self.assertEqual(connector.host, es_connector_conf["host"]) # default to elasticsearch
        self.assertEqual(connector.chunk_search, es_connector_conf["chunk_search"])  # default to 20
        self.assertEqual(connector.chunk, es_connector_conf["chunk"])  # default to 500
        self.assertEqual(connector.thread_count, es_connector_conf["thread_count"]) # default to 3
        self.assertEqual(connector.max_tries, 4)
        self.assertEqual(connector.safe, True)
        self.assertEqual(connector.sample, 500)


class CSVDatasetTestCase(TestCase):

    def setUp(self):
        config.init()
        config.read_conf()
        project_dir = config.conf["global"]["paths"]["projects"]
        self.temporary_project_folder = tempfile.mkdtemp(dir=project_dir)
        config.read_conf()
        self.project_name = path.basename(self.temporary_project_folder)
        dataset_conf = """\
        datasets:
          my_dataset:
            connector: upload
            table: my_dataset.csv
            type: csv
            sep: ";"
        """
        self.temporary_dataset_file = tempfile.NamedTemporaryFile(dir=self.temporary_project_folder, delete=True)
        self.temporary_dataset_file.write(dataset_conf)
        self.dataset_name = self.temporary_dataset_file.name

    def test_write(self):
        dataset = Dataset(self.dataset_name)
        data = [
            ["John", "Doe", "1956/01/03", "Connecticut"],
            ["Bob", "Smith", "1967/05/26", "Ohio"]

        ]
        columns = ["fist_name", "last_name", "date_of_birth", "state"]
        df = pd.DataFrame(data, columns=columns)
        dataset.write(df)

    def tearDown(self):
        self.temporary_dataset_file.close()
        shutil.rmtree(self.temporary_project_folder)










