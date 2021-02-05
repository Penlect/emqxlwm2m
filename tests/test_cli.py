
# Built-in
import unittest

# Package
from emqxlwm2m.cmdloop import create_args


class TestCreateArgs(unittest.TestCase):

    def test_one_arg(self):
        result = create_args("/1/2/3=123")
        self.assertDictEqual({"/1/2/3": "123"}, result)

    def test_multiple_args(self):
        result = create_args("/1/2/3=123 10/11/22=hello 1/2=True")
        expected = {"/1/2/3": "123", "10/11/22": "hello", "1/2": "True"}
        self.assertDictEqual(expected, result)

    def test_white_space(self):
        result = create_args("/1/2/3=a b c")
        expected = {"/1/2/3": "a b c"}
        self.assertDictEqual(expected, result)

    def test_multiple_white_space(self):
        result = create_args("/1/2/3=a b c 10/11/22=1 2 3 1/0=1/2/3 1/2=3/4")
        expected = {"/1/2/3": "a b c", "10/11/22": "1 2 3", "1/0": "1/2/3", "1/2": "3/4"}
        self.assertDictEqual(expected, result)
