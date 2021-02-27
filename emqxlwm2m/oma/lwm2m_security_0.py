"""Generated by emqxlwm2m.codegen at 2020-11-22 12:13:49

LwM2M Object: LWM2M Security
ID: 0, URN: urn:oma:lwm2m:oma:0, Mandatory, Multiple
"""

from emqxlwm2m.lwm2m import *


class LWM2MServerURI(Resource):
    """LWM2M  Server URI 0 - String, Single, Mandatory

    Uniquely identifies the LwM2M Server or LwM2M Bootstrap-Server. The
    format of the CoAP URI is defined in Section 6 of RFC 7252.
    """

    rid = 0
    operations = BS_RW
    type = "string"
    range = "0-255 bytes"
    unit = "N/A"
    mandatory = True
    multiple = False


class BootstrapServer(Resource):
    """Bootstrap-Server 1 - Boolean, Single, Mandatory

    Determines if the current instance concerns a LwM2M Bootstrap-Server
    (true) or a standard LwM2M Server (false)
    """

    rid = 1
    operations = BS_RW
    type = "boolean"
    range = "N/A"
    unit = "N/A"
    mandatory = True
    multiple = False


class SecurityMode(Resource):
    """Security Mode 2 - Integer, Single, Mandatory

    Determines which UDP payload security mode is used
    0: Pre-Shared Key mode
    1: Raw Public Key mode
    2: Certificate mode
    3: NoSec mode
    4: Certificate mode with EST
    """

    rid = 2
    operations = BS_RW
    type = "integer"
    range = "0-4"
    unit = "N/A"
    mandatory = True
    multiple = False


class PublicKeyOrIdentity(Resource):
    """Public Key or Identity 3 - Opaque, Single, Mandatory

    Stores the LwM2M Client’s Certificate (Certificate mode), public key
    (RPK mode) or PSK Identity (PSK mode). The format is defined in
    Section E.1.1 of the LwM2M version 1.0 specification.
    """

    rid = 3
    operations = BS_RW
    type = "opaque"
    range = "N/A"
    unit = "N/A"
    mandatory = True
    multiple = False


class ServerPublicKey(Resource):
    """Server Public Key 4 - Opaque, Single, Mandatory

    Stores the LwM2M Server’s or LwM2M Bootstrap-Server’s Certificate
    (Certificate mode), public key (RPK mode). The format is defined in
    Section E.1.1 of the LwM2M version 1.0 specification.
    """

    rid = 4
    operations = BS_RW
    type = "opaque"
    range = "N/A"
    unit = "N/A"
    mandatory = True
    multiple = False


class SecretKey(Resource):
    """Secret Key 5 - Opaque, Single, Mandatory

    Stores the secret key or private key of the security mode. The
    format of the keying material is defined by the security mode in
    Section E.1.1 of the LwM2M version 1.0 specification. This Resource
    MUST only be changed by a bootstrap-server and MUST NOT be readable
    by any server.
    """

    rid = 5
    operations = BS_RW
    type = "opaque"
    range = "N/A"
    unit = "N/A"
    mandatory = True
    multiple = False


class SMSSecurityMode(Resource):
    """SMS Security Mode 6 - Integer, Single, Optional

    Determines which SMS security mode is used (see section 7.2 of the
    LwM2M version 1.0 specification)

    0: Reserved for future use
    1: DTLS mode (Device terminated) PSK mode assumed
    2: Secure Packet Structure mode (Smartcard terminated)
    3: NoSec mode
    4: Reserved mode (DTLS mode with multiplexing Security Association
    support)

    5-203 : Reserved for future use
    204-255: Proprietary modes
    """

    rid = 6
    operations = BS_RW
    type = "integer"
    range = "0-255"
    unit = "N/A"
    mandatory = False
    multiple = False


class SMSBindingKeyParameters(Resource):
    """SMS Binding Key Parameters 7 - Opaque, Single, Optional

    Stores the KIc, KID, SPI and TAR. The format is defined in Section
    E.1.2 of the LwM2M version 1.0 specification.
    """

    rid = 7
    operations = BS_RW
    type = "opaque"
    range = "6 bytes"
    unit = "N/A"
    mandatory = False
    multiple = False


class SMSBindingSecretKeys(Resource):
    """SMS Binding Secret Key(s) 8 - Opaque, Single, Optional

    Stores the values of the key(s) for the SMS binding.
    This resource MUST only be changed by a bootstrap-server and MUST
    NOT be readable by any server.
    """

    rid = 8
    operations = BS_RW
    type = "opaque"
    range = "16-32-48 bytes"
    unit = "N/A"
    mandatory = False
    multiple = False


class LwM2MServerSMSNumber(Resource):
    """LwM2M Server SMS Number 9 - String, Single, Optional

    MSISDN used by the LwM2M Client to send messages to the LwM2M Server
    via the SMS binding.

    The LwM2M Client SHALL silently ignore any SMS originated from
    unknown MSISDN
    """

    rid = 9
    operations = BS_RW
    type = "string"
    range = "N/A"
    unit = "N/A"
    mandatory = False
    multiple = False


class ShortServerID(Resource):
    """Short Server ID 10 - Integer, Single, Optional

    This identifier uniquely identifies each LwM2M Server configured for
    the LwM2M Client.

    This Resource MUST be set when the Bootstrap-Server Resource has
    false value.

    Specific ID:0 and ID:65535 values MUST NOT be used for identifying
    the LwM2M Server (Section 6.3 of the LwM2M version 1.0
    specification).
    """

    rid = 10
    operations = BS_RW
    type = "integer"
    range = "1-65534"
    unit = "N/A"
    mandatory = False
    multiple = False


class ClientHoldOffTime(Resource):
    """Client Hold Off Time 11 - Integer, Single, Optional

    Relevant information for a Bootstrap-Server only.
    The number of seconds to wait before initiating a Client Initiated
    Bootstrap once the LwM2M Client has determined it should initiate
    this bootstrap mode.

    In case client initiated bootstrap is supported by the LwM2M Client,
    this resource MUST be supported.
    """

    rid = 11
    operations = BS_RW
    type = "integer"
    range = "N/A"
    unit = "s"
    mandatory = False
    multiple = False


class BootstrapServerAccountTimeout(Resource):
    """Bootstrap-Server Account Timeout 12 - Integer, Single, Optional

    The LwM2M Client MUST purge the LwM2M Bootstrap-Server Account after
    the timeout value given by this resource. The lowest timeout value
    is 1.

    If the value is set to 0, or if this resource is not instantiated,
    the Bootstrap-Server Account lifetime is infinite.
    """

    rid = 12
    operations = BS_RW
    type = "integer"
    range = "N/A"
    unit = "s"
    mandatory = False
    multiple = False


class LWM2MSecurity(ObjectDef):
    """LWM2M Security Object 0 - Mandatory, Multiple

    This LwM2M Object provides the keying material of a LwM2M Client
    appropriate to access a specified LwM2M Server. One Object Instance
    SHOULD address a LwM2M Bootstrap-Server.

    These LwM2M Object Resources MUST only be changed by a LwM2M
    Bootstrap-Server or Bootstrap from Smartcard and MUST NOT be
    accessible by any other LwM2M Server.
    """

    oid = 0
    mandatory = True
    multiple = True

    # ID=0, String, BS_RW, Single, Mandatory, range: 0-255 bytes, unit: N/A
    lwm2m_server_uri = LWM2MServerURI()

    # ID=1, Boolean, BS_RW, Single, Mandatory, range: N/A, unit: N/A
    bootstrap_server = BootstrapServer()

    # ID=2, Integer, BS_RW, Single, Mandatory, range: 0-4, unit: N/A
    security_mode = SecurityMode()

    # ID=3, Opaque, BS_RW, Single, Mandatory, range: N/A, unit: N/A
    public_key_or_identity = PublicKeyOrIdentity()

    # ID=4, Opaque, BS_RW, Single, Mandatory, range: N/A, unit: N/A
    server_public_key = ServerPublicKey()

    # ID=5, Opaque, BS_RW, Single, Mandatory, range: N/A, unit: N/A
    secret_key = SecretKey()

    # ID=6, Integer, BS_RW, Single, Optional, range: 0-255, unit: N/A
    sms_security_mode = SMSSecurityMode()

    # ID=7, Opaque, BS_RW, Single, Optional, range: 6 bytes, unit: N/A
    sms_binding_key_parameters = SMSBindingKeyParameters()

    # ID=8, Opaque, BS_RW, Single, Optional, range: 16-32-48 bytes, unit: N/A
    sms_binding_secret_key_s = SMSBindingSecretKeys()

    # ID=9, String, BS_RW, Single, Optional, range: N/A, unit: N/A
    lwm2m_server_sms_number = LwM2MServerSMSNumber()

    # ID=10, Integer, BS_RW, Single, Optional, range: 1-65534, unit: N/A
    short_server_id = ShortServerID()

    # ID=11, Integer, BS_RW, Single, Optional, range: N/A, unit: s
    client_hold_off_time = ClientHoldOffTime()

    # ID=12, Integer, BS_RW, Single, Optional, range: N/A, unit: s
    bootstrap_server_account_timeout = BootstrapServerAccountTimeout()
