"""Python package script"""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    long_description = readme_file.read()

with open('emqxlwm2m/__init__.py') as init:
    lines = [line for line in init.readlines() if line.startswith('__')]
exec(''.join(lines), globals())

setup(
    name='emqxlwm2m',
    version=__version__,
    author=__author__,
    author_email=__email__,
    description='A Python interface to the EMQx LwM2M plugin',
    long_description=long_description,
    license=__license__,
    keywords='emqx lwm2m emqx-lwm2m',
    url=__url__,
    packages=find_packages(),
    package_data=dict(emqxlwm2m=[
        'builtin_XMLs/*.xml',
        'builtin_XMLs/*.xsd'
    ]),
    install_requires=[
        'paho-mqtt>=1.5.0',
        # Only used for the CLI:
        'iterfzf>=0.5.0.20.0',
        'termcolor>=1.0.0',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython'
    ]
)
