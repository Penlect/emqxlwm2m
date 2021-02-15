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

   usage: python3 -m emqxlwm2m [--host HOST] [--port PORT]
                               [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                               [--timeout SEC] [--xml-path DIR]
                               [--ep-active EP_ACTIVE] [--ep-known EP_KNOWN]
                               [--ep-prefix EP_PREFIX] [--startup-script PATH]
                               [command]

   positional arguments:
     command               Select command: cmd, discover, read, write,
                           write_attr, execute, create, delete, observe,
                           cancel_observe, wiretap, uplink, downlink, requests,
                           responses, events, registrations, updates,
                           notifications, commands, discoverall, reboot, update,
                           firmware_update. Use with --help to see command
                           arguments.

   optional arguments:
     --host HOST           EMQx MQTT broker host (default: localhost)
     --port PORT, -p PORT  EMQx MQTT port (default: 1883)
     -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                           Logging level (default: INFO)
     --timeout SEC, -t SEC
                           Timeout when waiting for response in seconds (default:
                           60)
     --xml-path XML_PATH, -x XML_PATH
                           Directory containing LwM2M object definition XML-
                           files. Can be used multiple times to provide multiple
                           paths. Used when selecting a path interactively.
     --ep-active EP_ACTIVE
                           Default endpoint in interactive mode (subcommand
                           "cmd")
     --ep-known EP_KNOWN   Path to a text file listing known endpoints. Used for
                           interactive selection when endpoint is not specified
                           in command.
     --ep-prefix EP_PREFIX
                           Ensure endpoints starts with prefix.
     --startup-script PATH
                           Execute initialization commands from a script.


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

    $ python3 -m emqxlwm2m write urn:imei:123456789012345 /1/0/1=60

**Execute**: Execute the *reboot* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m execute urn:imei:123456789012345 /3/0/4

**Write-attr**: Set attributes (syntax: `[pmin,pmax]lt:st:gt`) on *battery level* resource:

.. code-block:: bash

    $ python3 -m emqxlwm2m attr urn:imei:123456789012345 /3/0/9=[60,120]5:10:95

Attributes can be omitted. To only set pmax to 100 seconds:

.. code-block:: bash

    $ python3 -m emqxlwm2m attr urn:imei:123456789012345 /3/0/9=[,100]

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
