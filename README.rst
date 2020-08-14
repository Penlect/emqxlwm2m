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

Read:

.. code-block:: bash

    $ python3 -m emqxlwm2m --host localhost --port 18830 read urn:imei:123456789012345 /3/0/18
    {'/3/0/18': '1.2.3'}

Write:

.. code-block:: bash

    $ python3 -m emqxlwm2m write urn:imei:123456789012345 /1/0/1 --value 60

Write-attr (syntax: [pmin,pmax]lt:st:gt):

.. code-block:: bash

    $ python3 -m emqxlwm2m attr urn:imei:123456789012345 /3/0/9 --value [60,120]5:10:95


.. _EMQx LwM2M plugin: https://github.com/emqx/emqx-lwm2m
