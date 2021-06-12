"""Python package script"""

import setuptools
import emqxlwm2m

with open("README.rst") as readme_file:
    long_description = readme_file.read()

setuptools.setup(
    name="emqxlwm2m",
    version=emqxlwm2m.__version__,
    author=emqxlwm2m.__author__,
    author_email=emqxlwm2m.__email__,
    description=emqxlwm2m.__doc__.splitlines()[0].strip(),
    long_description=long_description,
    license=emqxlwm2m.__license__,
    keywords="emqx lwm2m emqx-lwm2m",
    url=emqxlwm2m.__url__,
    packages=setuptools.find_packages(exclude=["tests"]),
    package_data=dict(emqxlwm2m=["oma/*.xml", "oma/*.xsd"]),
    install_requires=[
        "paho-mqtt>=1.5.0",
        "subpub>=1.0.0",
        # Only used for the CLI:
        "iterfzf>=0.5.0.20.0",
        "cmd2",
        "rich",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
