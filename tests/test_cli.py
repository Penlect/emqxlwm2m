# Built-in
import os
import unittest
from unittest.mock import patch, MagicMock, Mock

# Package
from emqxlwm2m.cmd2loop import ispath
import emqxlwm2m.cmd2loop
import emqxlwm2m.__main__ as cli

EP = "urn:imei:123"
TIMEOUT = 60


class TestIsPath(unittest.TestCase):
    def test_ispath(self):
        self.assertTrue(ispath("123"))
        self.assertTrue(ispath("1/2/3"))
        self.assertTrue(ispath("/1/2/3/"))

        self.assertTrue(ispath("/1/2/3/=asdf"))
        self.assertTrue(ispath("/1/2/3=asdf"))
        self.assertTrue(ispath("1/2/3/=asdf"))
        self.assertTrue(ispath("1/2/3=asdf"))

        self.assertFalse(ispath("1//2"))
        self.assertFalse(ispath("a/2"))
        self.assertFalse(ispath("1/b"))
        self.assertFalse(ispath("/"))
        self.assertFalse(ispath("hello there"))


class TestMain(unittest.TestCase):
    def setUp(self):
        self.patcher = patch(f"emqxlwm2m.engines.emqx.EMQxEngine")
        self.engine = self.patcher.start()
        self.endpoint = self.engine.via_mqtt().endpoint
        ep = MagicMock()
        ep.endpoint = EP
        self.endpoint.return_value = ep
        try:
            del os.environ["EMQXLWM2M_EP_PREFIX"]
        except KeyError:
            pass
        print()

    def teardown(self):
        self.patcher.stop()

    def test_discover(self):
        cli.main(["discover", EP, "1/2/3"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().discover.assert_called_once_with("1/2/3", timeout=None)

    def test_read(self):
        cli.main(["read", EP, "1/2/3"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().read.assert_called_once_with("1/2/3", timeout=None)

    def test_write(self):
        cli.main(["write", EP, "1/2/3", "--value", "123"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().write.assert_called_once_with(
            "1/2/3", 123, timeout=None
        )

    def test_write_whitespace(self):
        cli.main(["write", EP, "1/2/3", "--value", '"123 abc"'])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().write.assert_called_once_with(
            "1/2/3", "123 abc", timeout=None
        )

    def test_attr(self):
        cli.main(["attr", EP, "1/2/3", "--value", "[10,100]1:7:31"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().write_attr.assert_called_once_with(
            path="1/2/3", pmin=10, pmax=100, lt=1, st=7, gt=31, timeout=None
        )

    def test_execute(self):
        cli.main(["execute", EP, "1/2/3", "--arg", "order66"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().execute.assert_called_once_with(
            "1/2/3", "order66", timeout=None
        )

    def test_create(self):
        cli.main(["create", EP, "12345/0/1=hello", "12345/0/2=123"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().create.assert_called_once_with(
            "", {"12345/0/1": "hello", "12345/0/2": 123}, timeout=None
        )

    def test_create_whitespace(self):
        cli.main(["create", EP, '12345/0/1="hello world"', "12345/0/2=123"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().create.assert_called_once_with(
            "", {"12345/0/1": "hello world", "12345/0/2": 123}, timeout=None
        )

    def test_delete(self):
        cli.main(["delete", EP, "1/2/3"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().delete.assert_called_once_with("1/2/3", timeout=None)

    def test_observe(self):
        self.endpoint().observe.return_value = (MagicMock(), MagicMock())
        cli.main(["observe", EP, "1/2/3"])
        self.endpoint.assert_called_with(EP, TIMEOUT)
        self.endpoint().observe.assert_called_once_with(
            "1/2/3", queue=None, timeout=None
        )

    def test_cancel_observe(self):
        cli.main(["cancel-observe", EP, "1/2/3"])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        self.endpoint().cancel_observe.assert_called_once_with(
            "1/2/3", timeout=None
        )

    def test_registrations(self):
        cli.main(["registrations", EP, "--stop-after", "0"])
        self.endpoint.assert_called_with(EP, TIMEOUT)
        self.endpoint().registrations.assert_called()

    def test_updates(self):
        cli.main(["updates", EP, "--stop-after", "0"])
        self.endpoint.assert_called_with(EP, TIMEOUT)
        self.endpoint().updates.assert_called()

    def test_notifications(self):
        cli.main(["notifications", EP, "--stop-after", "0"])
        self.endpoint.assert_called_with(EP, TIMEOUT)
        self.endpoint().notifications.assert_called()

    def test_reboot(self):
        cli.main(["reboot", EP])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        # self.endpoint().execute.assert_called_once_with('/3/0/4', '')

    def test_update(self):
        cli.main(["update", EP])
        self.endpoint.assert_called_once_with(EP, TIMEOUT)
        # self.endpoint().execute.assert_called_once_with('/1/0/8', '')
