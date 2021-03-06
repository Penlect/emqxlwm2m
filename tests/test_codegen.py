# Built-in
import pathlib
import unittest

# Package
from emqxlwm2m import codegen
import emqxlwm2m.loadobjects


class TestCodegen(unittest.TestCase):
    def test_codegen(self):
        xmlfiles = [
            pathlib.Path("emqxlwm2m") / f
            for f in emqxlwm2m.loadobjects.XML_BUILTIN
        ]
        objects = emqxlwm2m.loadobjects.load_objects(xmlfiles)
        for xmlfile, obj in objects.items():
            with self.subTest(xml=xmlfile.name):
                content = codegen.generate_python_code(
                    codegen.PY_TEMPLATE, obj=obj
                )
                env = dict()
                exec(content, env, env)  # Same env instance
