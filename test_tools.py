#!/bin/env python3

import subprocess
import unittest
import tools

class TestSDK(unittest.TestCase):
    def test_installed_sdks(self):
        for sdk in tools.get_installed_sdks():
            text = "Using java version {} in this shell.".format(sdk)
            with self.subTest(sdk = sdk):
                result = subprocess.run(
                    tools.sdk_run(sdk, 'java -version'),
                    shell  = True,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.STDOUT
                )
                self.assertTrue(result.stdout.decode(encoding = 'utf-8').find(text) != -1)

    def test_sdk_run_raises_when_sdk_not_installed(self):
        with self.assertRaises(ValueError) as e:
            tools.sdk_run("something else", "some command")

    def test_sdk_home(self):
        for sdk in tools.get_installed_sdks():
            with self.subTest(sdk = sdk):
                home = tools.sdk_home(sdk)
                self.assertTrue(home.find('.sdkman/candidates/java/') != 0)
                self.assertTrue(home.find(sdk) != 0)

    def test_sdk_home_raises_when_sdk_not_installed(self):
        with self.assertRaises(ValueError):
            tools.sdk_home("something else")

if __name__ == '__main__':
    unittest.main()

