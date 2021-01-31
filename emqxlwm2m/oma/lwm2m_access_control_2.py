"""Generated by emqxlwm2m.codegen at 2020-11-22 12:13:49

LwM2M Object: LwM2M Access Control
ID: 2, URN: urn:oma:lwm2m:oma:2, Optional, Multiple
"""

from emqxlwm2m.lwm2m import *


class ObjectID(Resource):
    """Object ID 0 - Integer, Single, Mandatory

    Resources 0 and 1 point to the Object Instance for which the
    Instances of the ACL Resource of that Access Control Object Instance
    are applicable.
    """

    rid = 0
    operations = R
    type = 'integer'
    range = '1-65534'
    unit = 'N/A'
    mandatory = True
    multiple = False


class ObjectInstanceID(Resource):
    """Object Instance ID 1 - Integer, Single, Mandatory

    See above
    """

    rid = 1
    operations = R
    type = 'integer'
    range = '0-65535'
    unit = 'N/A'
    mandatory = True
    multiple = False


class ACL(Resource):
    """ACL 2 - Integer, Multiple, Optional

    The Resource Instance ID MUST be the Short Server ID of a certain
    LwM2M Server for which associated access rights are contained in the
    Resource Instance value.

    The Resource Instance ID 0 is a specific ID, determining the ACL
    Instance which contains the default access rights.

    Each bit set in the Resource Instance value, grants an access right
    to the LwM2M Server to the corresponding operation.

    The bit order is specified as below.
    1st LSB: R(Read, Observe, Write-Attributes)
    2nd LSB: W(Write)
    3rd LSB: E(Execute)
    4th LSB: D(Delete)
    5th LSB: C(Create)
    Other bits are reserved for future use.
    """

    rid = 2
    operations = RW
    type = 'integer'
    range = '16-bit'
    unit = 'N/A'
    mandatory = False
    multiple = True


class AccessControlOwner(Resource):
    """Access Control Owner 3 - Integer, Single, Mandatory

    Short Server ID of a certain LwM2M Server; only such an LwM2M Server
    can manage the Resources of this Object Instance.

    The specific value MAX_ID=65535 means this Access Control Object
    Instance is created and modified during a Bootstrap phase only.
    """

    rid = 3
    operations = RW
    type = 'integer'
    range = '0-65535'
    unit = 'N/A'
    mandatory = True
    multiple = False


class LwM2MAccessControl(ObjectDef):
    """LwM2M Access Control Object 2 - Optional, Multiple

    Access Control Object is used to check whether the LwM2M Server has
    access right for performing an operation.
    """

    oid = 2
    mandatory = False
    multiple = True

    # ID=0, Integer, R, Single, Mandatory, range: 1-65534, unit: N/A
    object_id = ObjectID()

    # ID=1, Integer, R, Single, Mandatory, range: 0-65535, unit: N/A
    object_instance_id = ObjectInstanceID()

    # ID=2, Integer, RW, Multiple, Optional, range: 16-bit, unit: N/A
    acl = ACL()

    # ID=3, Integer, RW, Single, Mandatory, range: 0-65535, unit: N/A
    access_control_owner = AccessControlOwner()
