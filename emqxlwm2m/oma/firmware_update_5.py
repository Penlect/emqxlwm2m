"""Generated by emqxlwm2m.codegen at 2020-11-22 12:13:49

LwM2M Object: Firmware Update
ID: 5, URN: urn:oma:lwm2m:oma:5, Optional, Single
"""

import enum
from emqxlwm2m.lwm2m import *


class Package(Resource):
    """Package 0 - Opaque, Single, Mandatory

    Firmware package
    """

    rid = 0
    operations = W
    type = 'opaque'
    range = 'N/A'
    unit = 'N/A'
    mandatory = True
    multiple = False


class PackageURI(Resource):
    """Package URI 1 - String, Single, Mandatory

    URI from where the device can download the firmware package by an
    alternative mechanism. As soon the device has received the Package
    URI it performs the download at the next practical opportunity.

    The URI format is defined in RFC 3986. For example,
    coaps://example.org/firmware is a syntactically valid URI. The URI
    scheme determines the protocol to be used. For CoAP this endpoint
    MAY be a LwM2M Server but does not necessarily need to be. A CoAP
    server implementing block-wise transfer is sufficient as a server
    hosting a firmware repository and the expectation is that this
    server merely serves as a separate file server making firmware
    images available to LwM2M Clients.
    """

    rid = 1
    operations = RW
    type = 'string'
    range = '0-255 bytes'
    unit = 'N/A'
    mandatory = True
    multiple = False


class Update(Resource):
    """Update 2 - N/a, Single, Mandatory

    Updates firmware by using the firmware package stored in Package,
    or, by using the firmware downloaded from the Package URI.

    This Resource is only executable when the value of the State
    Resource is Downloaded.
    """

    rid = 2
    operations = E
    type = 'N/A'
    range = 'N/A'
    unit = 'N/A'
    mandatory = True
    multiple = False


class State(Resource):
    """State 3 - Integer, Single, Mandatory

    Indicates current state with respect to this firmware update. This
    value is set by the LwM2M Client.

    0: Idle (before downloading or after successful updating)
    1: Downloading (The data sequence is on the way)
    2: Downloaded
    3: Updating
    If writing the firmware package to Package Resource is done, or, if
    the device has downloaded the firmware package from the Package URI
    the state changes to Downloaded.

    Writing an empty string to Package URI Resource or setting the
    Package Resource to NULL (‘\0’), resets the Firmware Update State
    Machine: the State Resource value is set to Idle and the Update
    Result Resource value is set to 0.

    When in Downloaded state, and the executable Resource Update is
    triggered, the state changes to Updating.

    If the Update Resource failed, the state returns at Downloaded.
    If performing the Update Resource was successful, the state changes
    from Updating to Idle.

    Firmware Update mechanisms are illustrated below in Figure 29 of the
    LwM2M version 1.0 specification.
    """

    class Enum(enum.Enum):
        IDLE = 0
        DOWNLOADING = 1
        DOWNLOADED = 2
        UPDATING = 3

    rid = 3
    operations = R
    type = Enum
    range = '0-3'
    unit = 'N/A'
    mandatory = True
    multiple = False


class UpdateResult(Resource):
    """Update Result 5 - Integer, Single, Mandatory

    Contains the result of downloading or updating the firmware
    0: Initial value. Once the updating process is initiated (Download
    /Update), this Resource MUST be reset to Initial value.

    1: Firmware updated successfully,
    2: Not enough flash memory for the new firmware package.
    3. Out of RAM during downloading process.
    4: Connection lost during downloading process.
    5: Integrity check failure for new downloaded package.
    6: Unsupported package type.
    7: Invalid URI
    8: Firmware update failed
    9: Unsupported protocol. A LwM2M client indicates the failure to
    retrieve the firmware image using the URI provided in the Package
    URI resource by writing the value 9 to the /5/0/5 (Update Result
    resource) when the URI contained a URI scheme unsupported by the
    client. Consequently, the LwM2M Client is unable to retrieve the
    firmware image using the URI provided by the LwM2M Server in the
    Package URI when it refers to an unsupported protocol.
    """

    class Enum(enum.Enum):
        INITIAL_VALUE = 0
        UPDATE_SUCCESSFUL = 1
        NOT_ENOUGH_FLASH = 2
        OUT_OF_RAM = 3
        CONNECTION_LOST = 4
        INTEGRITY_CHECK_FAILURE = 5
        UNSUPPORTED_PACKAGE_TYPE = 6
        INVALID_URI = 7
        UPDATE_FAILED = 8
        UNSUPPORTED_PROTOCOL = 9

    rid = 5
    operations = R
    type = Enum
    range = '0-9'
    unit = 'N/A'
    mandatory = True
    multiple = False


class PkgName(Resource):
    """PkgName 6 - String, Single, Optional

    Name of the Firmware Package
    """

    rid = 6
    operations = R
    type = 'string'
    range = '0-255 bytes'
    unit = 'N/A'
    mandatory = False
    multiple = False


class PkgVersion(Resource):
    """PkgVersion 7 - String, Single, Optional

    Version of the Firmware package
    """

    rid = 7
    operations = R
    type = 'string'
    range = '0-255 bytes'
    unit = 'N/A'
    mandatory = False
    multiple = False


class FirmwareUpdateProtocolSupport(Resource):
    """Firmware Update Protocol Support 8 - Integer, Multiple, Optional

    This resource indicates what protocols the LwM2M Client implements
    to retrieve firmware images. The LwM2M server uses this information
    to decide what URI to include in the Package URI. A LwM2M Server
    MUST NOT include a URI in the Package URI object that uses a
    protocol that is unsupported by the LwM2M client.

    For example, if a LwM2M client indicates that it supports CoAP and
    CoAPS then a LwM2M Server must not provide an HTTP URI in the Packet
    URI.

    The following values are defined by this version of the
    specification:

    0 – CoAP (as defined in RFC 7252) with the additional support for
    block-wise transfer. CoAP is the default setting.

    1 – CoAPS (as defined in RFC 7252) with the additional support for
    block-wise transfer

    2 – HTTP 1.1 (as defined in RFC 7230)
    3 – HTTPS 1.1 (as defined in RFC 7230)
    Additional values MAY be defined in the future. Any value not
    understood by the LwM2M Server MUST be ignored.
    """

    class Enum(enum.Enum):
        COAP = 0
        COAPS = 1
        HTTP = 2
        HTTPS = 3

    rid = 8
    operations = R
    type = Enum
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = True


class FirmwareUpdateDeliveryMethod(Resource):
    """Firmware Update Delivery Method 9 - Integer, Single, Mandatory

    The LwM2M Client uses this resource to indicate its support for
    transferring firmware images to the client either via the Package
    Resource (=push) or via the Package URI Resource (=pull) mechanism.

    0 – Pull only
    1 – Push only
    2 – Both. In this case the LwM2M Server MAY choose the preferred
    mechanism for conveying the firmware image to the LwM2M Client.
    """

    class Enum(enum.Enum):
        PULL_ONLY = 0
        PUSH_ONLY = 1
        BOTH = 2

    rid = 9
    operations = R
    type = Enum
    range = 'N/A'
    unit = 'N/A'
    mandatory = True
    multiple = False


class FirmwareUpdate(ObjectDef):
    """Firmware Update Object 5 - Optional, Single

    This LwM2M Object enables management of firmware which is to be
    updated. This Object includes installing firmware package, updating
    firmware, and performing actions after updating firmware. The
    firmware update MAY require to reboot the device; it will depend on
    a number of factors, such as the operating system architecture and
    the extent of the updated software.

    The envisioned functionality with LwM2M version 1.0 is to allow a
    LwM2M Client to connect to any LwM2M version 1.0 compliant Server to
    obtain a firmware imagine using the object and resource structure
    defined in this section experiencing communication security
    protection using DTLS. There are, however, other design decisions
    that need to be taken into account to allow a manufacturer of a
    device to securely install firmware on a device. Examples for such
    design decisions are how to manage the firmware update repository at
    the server side (which may include user interface considerations),
    the techniques to provide additional application layer security
    protection of the firmware image, how many versions of firmware
    imagines to store on the device, and how to execute the firmware
    update process considering the hardware specific details of a given
    IoT hardware product. These aspects are considered to be outside the
    scope of the LwM2M version 1.0 specification.

    A LwM2M Server may also instruct a LwM2M Client to fetch a firmware
    image from a dedicated server (instead of pushing firmware imagines
    to the LwM2M Client). The Package URI resource is contained in the
    Firmware object and can be used for this purpose.

    A LwM2M Client MUST support block-wise transfer [CoAP_Blockwise] if
    it implements the Firmware Update object.

    A LwM2M Server MUST support block-wise transfer. Other protocols,
    such as HTTP/HTTPs, MAY also be used for downloading firmware
    updates (via the Package URI resource). For constrained devices it
    is, however, RECOMMENDED to use CoAP for firmware downloads to avoid
    the need for additional protocol implementations.
    """

    oid = 5
    mandatory = False
    multiple = False

    # ID=0, Opaque, W, Single, Mandatory, range: N/A, unit: N/A
    package = Package()

    # ID=1, String, RW, Single, Mandatory, range: 0-255 bytes, unit: N/A
    package_uri = PackageURI()

    # ID=2, N/a, E, Single, Mandatory, range: N/A, unit: N/A
    update = Update()

    # ID=3, Integer, R, Single, Mandatory, range: 0-3, unit: N/A
    state = State()

    # ID=5, Integer, R, Single, Mandatory, range: 0-9, unit: N/A
    update_result = UpdateResult()

    # ID=6, String, R, Single, Optional, range: 0-255 bytes, unit: N/A
    pkgname = PkgName()

    # ID=7, String, R, Single, Optional, range: 0-255 bytes, unit: N/A
    pkgversion = PkgVersion()

    # ID=8, Integer, R, Multiple, Optional, range: N/A, unit: N/A
    firmware_update_protocol_support = FirmwareUpdateProtocolSupport()

    # ID=9, Integer, R, Single, Mandatory, range: N/A, unit: N/A
    firmware_update_delivery_method = FirmwareUpdateDeliveryMethod()

