#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import json
import os
import sys
import string
import random
import tempfile

try:
    from Pilot.pilotTools import CommandBase, PilotParams
except ImportError:
    from pilotTools import CommandBase, PilotParams

import unittest

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestPilotParams(unittest.TestCase):
    @patch("sys.argv")
    def test_pilotParamsInit(self, argvmock):
        argvmock.__getitem__.return_value = [
            "-z",
            "-d",
            "-g",
            "dummyURL",
            "-F",
            "tests/pilot.json",
        ]

        pp = PilotParams()

        argvmock.__getitem__.assert_called()
        self.assertEqual(argvmock.__getitem__.call_count, 2)  # 2 getopt calls
        self.assertTrue(pp.pilotLogging)
        self.assertEqual(pp.loggerURL, "dummyURL")
        self.assertTrue(pp.debugFlag)

    def test_getOptionForPaths(self):
        """Test option preference by path (later paths have higher preference)"""

        basedir = os.path.dirname(__file__)
        jsonFile = os.path.join(basedir, "../../tests/CI/pilot_newSchema.json")
        vo = "gridpp"
        setup = "DIRAC-Certification"
        paths = ["/Defaults/Pilot", "/%s/Pilot" % setup, "/%s/Defaults/Pilot" % vo, "/%s/%s/Pilot" % (vo, setup)]
        with open(jsonFile, "r") as fp:
            jsonDict = json.load(fp)
        res = PilotParams.getOptionForPaths(paths, jsonDict)
        self.assertEqual(res["RemoteLogging"], "True")
        self.assertEqual(res["UploadSE"], "UKI-LT2-IC-HEP-disk")
        del jsonDict[vo][setup]["Pilot"]["RemoteLogging"]  # remove a vo-specific settings, a default value is False:
        res = PilotParams.getOptionForPaths(paths, jsonDict)
        self.assertEqual(res["RemoteLogging"], "False")

    @patch.object(PilotParams, "_PilotParams__getSearchPaths")
    @patch("sys.argv")
    def test_pilotOptions(self, argvmock, mockPaths):
        # no -z, no -g when  the new JSON format in use.
        basedir = os.path.dirname(__file__)
        argvmock.__getitem__.return_value = [
            "-F",
            os.path.join(basedir, "../../tests/CI/pilot_newSchema.json"),
            "-N",
            "TEST_type_CE",
            "--gridCEType",
            "TEST",
        ]

        vo = "gridpp"
        setup = "DIRAC-Certification"
        paths = [
            "/Defaults/Pilot",
            "/%s/Pilot" % setup,
            "/%s/Defaults/Pilot" % vo,
            "/%s/%s/Pilot" % (vo, setup),
        ]
        mockPaths.return_value = paths
        pp = PilotParams()
        lTESTcommands = [
            "CheckWorkerNode",
            "InstallDIRAC",
            "ConfigureBasics",
            "CheckCECapabilities",
            "CheckWNCapabilities",
            "ConfigureSite",
            "ConfigureArchitecture",
            "ConfigureCPURequirements",
        ]

        pp.gridCEType = "TEST"

        res = pp.getPilotOptionsDict()
        logURL = "https://lbvobox70.cern.ch:8443/WorkloadManagement/TornadoPilotLogging"
        self.assertEqual(res.get("RemoteLoggerURL"), logURL)
        self.assertEqual(pp.loggerURL, logURL)
        self.assertEqual(res.get("RemoteLogging"), "True")
        self.assertIs(pp.pilotLogging, True)
        self.assertEqual(res.get("UploadPath"), "/gridpp/pilotlogs/")
        self.assertTrue("Commands" in res)
        self.assertEqual(res["Commands"].get(pp.gridCEType), lTESTcommands)
        self.assertEqual(pp.commands, lTESTcommands)
        self.assertEqual(pp.releaseVersion, "VAR_DIRAC_VERSION")


class TestCommandBase(unittest.TestCase):
    def setUp(self):
        # These temporary files, opened in a binary mode, will act as standard stream pipes for `Popen`
        self.stdout_mock = tempfile.NamedTemporaryFile(mode="rb+", delete=False)
        self.stderr_mock = tempfile.NamedTemporaryFile(mode="rb+", delete=False)

    def tearDown(self):
        # At the end of the test, we'll close and remove the created files
        self.stdout_mock.close()
        os.remove(self.stdout_mock.name)
        os.remove(self.stderr_mock.name)

    @patch(("sys.argv"))
    @patch("subprocess.Popen")
    def test_executeAndGetOutput(self, popenMock, argvmock):
        argvmock.__getitem__.return_value = [
            "-d",
            "-g",
            "dummyURL",
            "-F",
            "tests/pilot.json",
        ]

        for size in [1000, 1024, 1025, 2005]:
            random_str = "".join(random.choice(string.ascii_letters + "\n") for i in range(size))
            if sys.version_info.major == 3:
                random_bytes = random_str.encode("UTF-8")
                self.stdout_mock.write(random_bytes)
            else:
                self.stdout_mock.write(random_str)
            self.stdout_mock.seek(0)
            if sys.version_info.major == 3:
                self.stderr_mock.write("Errare humanum est!".encode("UTF-8"))
            else:
                self.stderr_mock.write("Errare humanum est!")
            self.stderr_mock.seek(0)
            pp = PilotParams()
            cBase = CommandBase(pp)
            popenMock.return_value.stdout = self.stdout_mock
            popenMock.return_value.stderr = self.stderr_mock
            outData = cBase.executeAndGetOutput("dummy")
            popenMock.assert_called()
            self.assertEqual(outData[1], random_str)
            self.stdout_mock.seek(0)
            self.stderr_mock.seek(0)
            self.stdout_mock.truncate()
            self.stderr_mock.truncate()


class TestSimplePilotLogger(unittest.TestCase):
    def test_SimplePilotLogger(self):
        uuid = "37356d94-15c6-11e6-a600-606c663dde16"


if __name__ == "__main__":
    unittest.main()