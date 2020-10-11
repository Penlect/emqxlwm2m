
# Built-in
import collections
import os
import re
import operator
import pathlib
import textwrap
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from pkg_resources import resource_filename as pkg_path

XML_BUILTIN = (
    'builtin_XMLs/LWM2M_Security-v1_0.xml',
    'builtin_XMLs/LWM2M_Server-v1_0.xml',
    'builtin_XMLs/LWM2M_Access_Control-v1_0_1.xml',
    'builtin_XMLs/LWM2M_Device-v1_0_1.xml',
    'builtin_XMLs/LWM2M_Firmware_Update-v1_0_1.xml',
    'builtin_XMLs/LWM2M_Location-v1_0.xml',
    'builtin_XMLs/LWM2M_Connectivity_Statistics-v1_0_1.xml',
)

def _node_text(n: Element) -> str:
    return (n.text if n.text is not None else '').strip()

def _sanitize_snake_name(n: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]+', '_', n).strip('_').lower()

def _sanitize_class_name(n: str) -> str:
    name = re.sub(r'[^a-zA-Z0-9]+', '_', n).strip('_').lower()
    name = name.title()
    name = name.replace('_', '')
    return name


class ResourceDef(collections.namedtuple('ResourceDef', ['rid', 'name', 'operations', 'multiple', 'mandatory', 'type',
                                                         'range_enumeration', 'units', 'description'])):
    @property
    def mandatory_str(self) -> str:
        return 'Mandatory' if self.mandatory else 'Optional'

    @property
    def multiple_str(self):
        return 'Multiple' if self.multiple else 'Single'

    @property
    def name_class(self) -> str:
        return _sanitize_class_name(self.name)

    @property
    def name_snake(self) -> str:
        return _sanitize_snake_name(self.name)

    @property
    def op(self) -> str:
        result = self.operations
        if self.multiple:
            result += 'M'
        return result

    @classmethod
    def from_etree(cls, res: Element) -> 'ResourceDef':
        return cls(
            rid=int(res.get('ID')),
            name=_node_text(res.find('Name')),
            operations=_node_text(res.find('Operations')).upper()
                       or 'BS_RW', # no operations = resource modifiable by Bootstrap Server
            multiple={'Single': False, 'Multiple': True}[_node_text(res.find('MultipleInstances'))],
            mandatory={'Optional': False, 'Mandatory': True}[_node_text(res.find('Mandatory'))],
            type=(_node_text(res.find('Type')).lower() or 'N/A'),
            range_enumeration=(_node_text(res.find('RangeEnumeration')) or 'N/A'),
            units=(_node_text(res.find('Units')) or 'N/A'),
            description=textwrap.fill(_node_text(res.find('Description'))))


class ObjectDef(collections.namedtuple('ObjectDef',
                                       ['oid', 'name', 'description', 'urn', 'multiple', 'mandatory', 'resources'])):
    @property
    def name_snake(self) -> str:
        return _sanitize_snake_name(self.name)

    @property
    def name_module(self) -> str:
        return f'{self.name_snake}_{self.oid}'

    @property
    def name_class(self) -> str:
        return _sanitize_class_name(self.name)

    @property
    def mandatory_str(self) -> str:
        return 'Mandatory' if self.mandatory else 'Optional'

    @property
    def multiple_str(self):
        return 'Multiple' if self.multiple else 'Single'

    @staticmethod
    def parse_resources(obj: ElementTree):
        return sorted([ResourceDef.from_etree(item) for item in obj.find('Resources').findall('Item')],
                       key=operator.attrgetter('rid'))

    @classmethod
    def from_etree(cls, obj: ElementTree) -> 'ObjectDef':
        resources = ObjectDef.parse_resources(obj)
        return cls(
            name=_node_text(obj.find('Name')),
            description=textwrap.fill(_node_text(obj.find('Description1'))),
            oid=int(_node_text(obj.find('ObjectID'))),
            urn=_node_text(obj.find('ObjectURN')),
            multiple={'Single': False, 'Multiple': True}[_node_text(obj.find('MultipleInstances'))],
            mandatory={'Optional': False, 'Mandatory': True}[_node_text(obj.find('Mandatory'))],
            resources=resources)


def find_xml_files(xml_dir):
    """Yield full paths of xml files found in `xml_dir` directory"""
    for name in os.listdir(xml_dir):
        if name.lower().endswith('.xml'):
            yield os.path.join(xml_dir, name)


def load_object(xml_file):
    if isinstance(xml_file, str):
        with open(xml_file) as f:
            content = f.read()
    else:
        content = xml_file.read()
    tree = ElementTree.fromstring(content)
    xmlobj = tree.find('Object')
    return ObjectDef.from_etree(xmlobj)


def load_objects(xml_paths, load_builtin=True):
    """Load `Objects` in xml definitions"""

    # Find all xml files
    xml_files = list()
    if isinstance(xml_paths, str):
        xml_paths = [xml_paths]
    for path in xml_paths:
        if os.path.isdir(path):
            for x in find_xml_files(path):
                xml_files.append(x)
        else:
            xml_files.append(path)
    if load_builtin:
        xml_files.extend([pkg_path(__package__, x) for x in XML_BUILTIN])

    # Parse xml files
    objects = dict()
    for xml_file in xml_files:
        objects[pathlib.Path(xml_file)] = load_object(xml_file)
    return objects
