
# Built-in
import unittest

# Package
from emqxlwm2m.lwm2m import Attributes


class TestAttributes(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(Attributes()), '')
        self.assertEqual(str(Attributes(pmin=1)), '[1,]')
        self.assertEqual(str(Attributes(pmax=2)), '[,2]')
        self.assertEqual(str(Attributes(pmin=1, pmax=2)), '[1,2]')
        self.assertEqual(str(Attributes(lt=3)), '3::')
        self.assertEqual(str(Attributes(st=4)), ':4:')
        self.assertEqual(str(Attributes(gt=5)), '::5')
        self.assertEqual(str(Attributes(lt=3, st=4, gt=5)), '3:4:5')
        self.assertEqual(str(Attributes(pmin=1, pmax=2, lt=3, st=4, gt=5)), '[1,2]3:4:5')

    def test_from_string(self):
        self.assertEqual(Attributes(), Attributes.from_string(''))
        self.assertEqual(Attributes(pmin=1), Attributes.from_string('[1,]'))
        self.assertEqual(Attributes(pmax=2), Attributes.from_string('[,2]'))
        self.assertEqual(Attributes(pmin=1, pmax=2), Attributes.from_string('[1,2]'))
        self.assertEqual(Attributes(lt=3), Attributes.from_string('3::'))
        self.assertEqual(Attributes(st=4), Attributes.from_string(':4:'))
        self.assertEqual(Attributes(gt=5), Attributes.from_string('::5'))
        self.assertEqual(Attributes(lt=3, st=4, gt=5), Attributes.from_string('3:4:5'))
        self.assertEqual(Attributes(pmin=1, pmax=2, lt=3, st=4, gt=5), Attributes.from_string('[1,2]3:4:5'))

    def test_len(self):
        self.assertEqual(len(Attributes()), 0)
        self.assertEqual(len(Attributes(pmin=1, pmax=2, lt=3, st=4, gt=5)), 5)
