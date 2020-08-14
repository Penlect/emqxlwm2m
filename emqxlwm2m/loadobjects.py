
# Built-in
import os
from pkg_resources import resource_filename as pkg_path

# PyPI
import xmlschema

XML_SCHEMA = 'builtin_XMLs/LWM2M.xsd'
XML_BUILTIN = (
    'builtin_XMLs/LWM2M_Security-v1_0.xml',
    'builtin_XMLs/LWM2M_Server-v1_0.xml',
    'builtin_XMLs/LWM2M_Access_Control-v1_0_1.xml',
    'builtin_XMLs/LWM2M_Device-v1_0_1.xml',
    'builtin_XMLs/LWM2M_Firmware_Update-v1_0_1.xml',
    'builtin_XMLs/LWM2M_Location-v1_0.xml',
    'builtin_XMLs/LWM2M_Connectivity_Statistics-v1_0_1.xml',
)


def find_xml_files(*xml_dirs):
    """Yield full paths of xml files found in directories"""
    for path in xml_dirs:
        for name in os.listdir(path):
            if name.lower().endswith('.xml'):
                yield os.path.join(path, name)


def load_objects(xml_dirs, load_builtin=True):
    """Load `Objects` in xml definitions"""
    xsd = pkg_path(__package__, XML_SCHEMA)
    xs = xmlschema.XMLSchema(xsd)
    if isinstance(xml_dirs, str):
        xml_dirs = [xml_dirs]
    xml_files = list(find_xml_files(*xml_dirs))
    if load_builtin:
        xml_files.extend([pkg_path(__package__, x) for x in XML_BUILTIN])
    objects = list()
    for file in xml_files:
        data = xs.to_dict(file)
        objects.append(data['Object'])
    return objects
