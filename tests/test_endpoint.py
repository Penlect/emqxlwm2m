
# Built-in
import logging
import unittest
from unittest.mock import MagicMock


# Package
from emqxlwm2m.engines.emqx import EMQxEngine
from emqxlwm2m import lwm2m

logging.basicConfig(level=logging.DEBUG)
EP = 'my:endpoint'


class TestEndpoint(unittest.TestCase):

    def setUp(self):
        print()
        c = MagicMock()
        self.engine = EMQxEngine(c)
        self.engine.send = MagicMock()
        self.engine.on_connect(None, None, None, None)
        self.engine.__enter__()
        self.ep = self.engine.endpoint(EP)

    def tearDown(self):
        self.engine.__exit__(None, None, None)

    def test_discover_request(self):
        req = lwm2m.DiscoverRequest(EP, '/1/0')

        self.ep.discover('/1/0')
        self.engine.send.assert_called_once_with(req, None)

        self.ep.discover('/1/0', timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_read_request(self):
        req = lwm2m.ReadRequest(EP, '/1/0')

        self.ep.read('/1/0')
        self.engine.send.assert_called_once_with(req, None)

        self.ep.read('/1/0', timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_write_request(self):
        req = lwm2m.WriteRequest(EP, {'/1/0/1': 123})

        self.ep.write('/1/0/1', 123)
        self.engine.send.assert_called_once_with(req, None)

        self.ep.write('/1/0/1', 123, timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_execute_request(self):
        req = lwm2m.ExecuteRequest(EP, '/3/0/4', '')

        self.ep.execute('/3/0/4', '')
        self.engine.send.assert_called_once_with(req, None)

        self.ep.execute('/3/0/4', '', timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_create_request(self):
        req = lwm2m.CreateRequest(EP, {
            '/123/1/0': 'test', '/123/1/1': 321
        })

        self.ep.create({'/123/1/0': 'test', '/123/1/1': 321})
        self.engine.send.assert_called_once_with(req, None)

        self.ep.create({'/123/1/0': 'test', '/123/1/1': 321}, timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_delete_request(self):
        req = lwm2m.DeleteRequest(EP, '/123/0/0')

        self.ep.delete('/123/0/0')
        self.engine.send.assert_called_once_with(req, None)

        self.ep.delete('/123/0/0', timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_observe_request(self):
        req = lwm2m.ObserveRequest(EP, '/123/0/0')

        self.ep.observe('/123/0/0')
        self.engine.send.assert_called_once_with(req, None)

        self.ep.observe('/123/0/0', timeout=1)
        self.engine.send.assert_called_with(req, 1)

    def test_cancel_observe_request(self):
        req = lwm2m.CancelObserveRequest(EP, '/123/0/0')

        self.ep.cancel_observe('/123/0/0')
        self.engine.send.assert_called_once_with(req, None)

        self.ep.cancel_observe('/123/0/0', timeout=1)
        self.engine.send.assert_called_with(req, 1)
