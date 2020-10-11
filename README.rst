Welcome to emqxlwm2m
====================

This package provides a command line interface to the `EMQx LwM2M
plugin`_.

It supports read, discover, write, write-attr, execute, create,
delete. It also has some handy features for tracking notifications,
etc.

*NOTE:* This package is still in pre-alpha stage and backwards
incompatible changes are likely in the releases prior to version
1.0.0.


Usage and command line options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::


   usage: python3 -m emqxlwm2m [-h] [--host HOST] [--port PORT]
                            [--known-endpoints KNOWN_ENDPOINTS]
                            [--xml-path XML_PATH]
                            [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--echo]
                            [--value VALUE] [--interval INTERVAL]
                            [--timeout TIMEOUT]
   [{reboot,notifications,create,write,delete,update,updates,read,discoverall,execute,registrations,cancel-observe,observe,?,discover,attr,endpoints}]
   [endpoint] [path]

   positional arguments:
   {reboot,notifications,create,write,delete,update,updates,read,discoverall,execute,registrations,cancel-observe,observe,?,discover,attr,endpoints}
   endpoint              LwM2M endpoint client name
   path                  LwM2M object/instance/resource path

   optional arguments:
   -h, --help            show this help message and exit
   --host HOST           EMQx MQTT broker host
   --port PORT, -p PORT  EMQx MQTT port
   --known-endpoints KNOWN_ENDPOINTS
   Path to list of known endpoints. Used for interactive
   selection.
   --xml-path XML_PATH, -x XML_PATH
   Directory with xml lwm2m object definitions. Can be
   used multiple times to provide multiple paths.
   -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
   Set the logging level
   --echo                Print endpoint and path when selected with fzf.
   --value VALUE, -v VALUE
   Value to use in context of command.
   --interval INTERVAL, -i INTERVAL
   Repeat action with interval. Seconds.
   --timeout TIMEOUT, -t TIMEOUT
   Timeout when waiting for response. Seconds.


Installation
^^^^^^^^^^^^
From PyPI:

.. code-block:: bash

    $ python3 -m pip install emqxlwm2m


Examples
^^^^^^^^

**Read**: Read *hardware version* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m --host localhost --port 1883 read urn:imei:123456789012345 /3/0/18
    {'/3/0/18': '1.2.3'}

**Write**: Set the *lifetime* resource to 60 seconds:

.. code-block:: bash

    $ python3 -m emqxlwm2m write urn:imei:123456789012345 /1/0/1 --value 60

**Execute**: Execute the *reboot* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m execute urn:imei:123456789012345 /3/0/4

**Write-attr**: Set attributes (syntax: `[pmin,pmax]lt:st:gt`) on *battery level* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m attr urn:imei:123456789012345 /3/0/9 --value [60,120]5:10:95

Attributes can be omitted. To only set pmax to 100 seconds:

.. code-block:: bash

    $ python3 -m emqxlwm2m attr urn:imei:123456789012345 /3/0/9 --value [,100]

**Discover**: Discover instances/resources and their attributs, for
example, the *battery level* attribute previously set:

.. code-block:: bash

    $ python3 -m emqxlwm2m discover urn:imei:123456789012345 /3/0/9
    {'/3/0/9': {'pmax': '100', 'gt': '95', 'lt': '5', 'st': '10', 'pmin': '60'}}

**Observe**: Observe *battery level* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m observe urn:imei:123456789012345 /3/0/9

**Cancel-Observe**: Cancel observe on *battery level* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m cancel-observe urn:imei:123456789012345 /3/0/9


.. _EMQx LwM2M plugin: https://github.com/emqx/emqx-lwm2m
