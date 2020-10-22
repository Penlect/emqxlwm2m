
# Built-in
import unittest

# Package
from emqxlwm2m.lwm2m import Path


class TestPath(unittest.TestCase):
    """Test LwM2M Path"""

    def test_duplicated_slash(self):
        p = Path('1/2//3///4///')
        self.assertNotIn('//', p)
        self.assertEqual('1/2/3/4/', p)

    def test_parts(self):
        p = Path('1/2/3/4')
        self.assertListEqual(['1', '2', '3', '4'], p.parts)

    def test_oid(self):
        self.assertEqual(Path('1/2/3/4').oid, 1)

    def test_iid(self):
        self.assertEqual(Path('1/2/3/4').iid, 2)

    def test_rid(self):
        self.assertEqual(Path('1/2/3/4').rid, 3)

    def test_riid(self):
        self.assertEqual(Path('1/2/3/4').riid, 4)

    def test_dict(self):
        self.assertDictEqual(Path.dict({'1/2': 123}), {Path('1/2'): 123})

    def test_level(self):
        self.assertEqual(Path('').level, 'root')
        self.assertEqual(Path('1').level, 'object')
        self.assertEqual(Path('1/2').level, 'object_instance')
        self.assertEqual(Path('1/2/3').level, 'resource')
        self.assertEqual(Path('1/2/3/4').level, 'resource_instance')
