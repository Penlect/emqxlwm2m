"""Generated by emqxlwm2m.codegen at 2020-11-22 12:13:49

LwM2M Object: Device
ID: 3, URN: urn:oma:lwm2m:oma:3, Mandatory, Single
"""

from emqxlwm2m.lwm2m import *


class Manufacturer(Resource):
    """Manufacturer 0 - String, Single, Optional

    Human readable manufacturer name
    """

    rid = 0
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class ModelNumber(Resource):
    """Model Number 1 - String, Single, Optional

    A model identifier (manufacturer specified string)
    """

    rid = 1
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class SerialNumber(Resource):
    """Serial Number 2 - String, Single, Optional

    Serial Number
    """

    rid = 2
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class FirmwareVersion(Resource):
    """Firmware Version 3 - String, Single, Optional

    Current firmware version of the Device.The Firmware Management
    function could rely on this resource.
    """

    rid = 3
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class Reboot(Resource):
    """Reboot 4 - N/a, Single, Mandatory

    Reboot the LwM2M Device to restore the Device from unexpected
    firmware failure.
    """

    rid = 4
    operations = E
    type = 'N/A'
    range = 'N/A'
    unit = 'N/A'
    mandatory = True
    multiple = False


class FactoryReset(Resource):
    """Factory Reset 5 - N/a, Single, Optional

    Perform factory reset of the LwM2M Device to make the LwM2M Device
    to go through initial deployment sequence where provisioning and
    bootstrap sequence is performed. This requires client ensuring post
    factory reset to have minimal information to allow it to carry out
    one of the bootstrap methods specified in section 5.2.3.

    When this Resource is executed, “De-register” operation MAY be sent
    to the LwM2M Server(s) before factory reset of the LwM2M Device.
    """

    rid = 5
    operations = E
    type = 'N/A'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class AvailablePowerSources(Resource):
    """Available Power Sources 6 - Integer, Multiple, Optional

    0 – DC power
    1 – Internal Battery
    2 – External Battery
    4 – Power over Ethernet
    5 – USB
    6 – AC (Mains) power
    7 – Solar
    The same Resource Instance ID MUST be used to associate a given
    Power Source (Resource ID:6) with its Present Voltage (Resource
    ID:7) and its Present Current (Resource ID:8)
    """

    rid = 6
    operations = R
    type = 'integer'
    range = '0-7'
    unit = 'N/A'
    mandatory = False
    multiple = True


class PowerSourceVoltage(Resource):
    """Power Source Voltage 7 - Integer, Multiple, Optional

    Present voltage for each Available Power Sources Resource Instance.
    """

    rid = 7
    operations = R
    type = 'integer'
    range = 'N/A'
    unit = 'mV'
    mandatory = False
    multiple = True


class PowerSourceCurrent(Resource):
    """Power Source Current 8 - Integer, Multiple, Optional

    Present current for each Available Power Source.
    """

    rid = 8
    operations = R
    type = 'integer'
    range = 'N/A'
    unit = 'mA'
    mandatory = False
    multiple = True


class BatteryLevel(Resource):
    """Battery Level 9 - Integer, Single, Optional

    Contains the current battery level as a percentage (with a range
    from 0 to 100). This value is only valid for the Device internal
    Battery if present (one Available Power Sources Resource Instance is
    1).
    """

    rid = 9
    operations = R
    type = 'integer'
    range = '0-100'
    unit = '%'
    mandatory = False
    multiple = False


class MemoryFree(Resource):
    """Memory Free 10 - Integer, Single, Optional

    Estimated current available amount of storage space which can store
    data and software in the LwM2M Device (expressed in kilobytes).
    """

    rid = 10
    operations = R
    type = 'integer'
    range = 'N/A'
    unit = 'KB'
    mandatory = False
    multiple = False


class ErrorCode(Resource):
    """Error Code 11 - Integer, Multiple, Mandatory

    0=No error
    1=Low battery power
    2=External power supply off
    3=GPS module failure
    4=Low received signal strength
    5=Out of memory
    6=SMS failure
    7=IP connectivity failure
    8=Peripheral malfunction

    When the single Device Object Instance is initiated, there is only
    one error code Resource Instance whose value is equal to 0 that
    means no error. When the first error happens, the LwM2M Client
    changes error code Resource Instance to any non-zero value to
    indicate the error type. When any other error happens, a new error
    code Resource Instance is created. When an error associated with a
    Resource Instance is no longer present, that Resource Instance is
    deleted. When the single existing error is no longer present, the
    LwM2M Client returns to the original no error state where Instance 0
    has value 0.

    This error code Resource MAY be observed by the LwM2M Server. How to
    deal with LwM2M Client’s error report depends on the policy of the
    LwM2M Server.
    """

    rid = 11
    operations = R
    type = 'integer'
    range = '0-8'
    unit = 'N/A'
    mandatory = True
    multiple = True


class ResetErrorCode(Resource):
    """Reset Error Code 12 - N/a, Single, Optional

    Delete all error code Resource Instances and create only one zero-
    value error code that implies no error, then re-evaluate all error
    conditions and update and create Resources Instances to capture all
    current error conditions.
    """

    rid = 12
    operations = E
    type = 'N/A'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class CurrentTime(Resource):
    """Current Time 13 - Time, Single, Optional

    Current UNIX time of the LwM2M Client.
    The LwM2M Client should be responsible to increase this time value
    as every second elapses.

    The LwM2M Server is able to write this Resource to make the LwM2M
    Client synchronized with the LwM2M Server.
    """

    rid = 13
    operations = RW
    type = 'time'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class UTCOffset(Resource):
    """UTC Offset 14 - String, Single, Optional

    Indicates the UTC offset currently in effect for this LwM2M Device.
    UTC+X [ISO 8601].
    """

    rid = 14
    operations = RW
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class Timezone(Resource):
    """Timezone 15 - String, Single, Optional

    Indicates in which time zone the LwM2M Device is located, in IANA
    Timezone (TZ) database format.
    """

    rid = 15
    operations = RW
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class SupportedBindingAndModes(Resource):
    """Supported Binding and Modes 16 - String, Single, Mandatory

    Indicates which bindings and modes are supported in the LwM2M
    Client. The possible values of Resource are combination of "U" or
    "UQ" and "S" or "SQ".
    """

    rid = 16
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = True
    multiple = False


class DeviceType(Resource):
    """Device Type 17 - String, Single, Optional

    Type of the device (manufacturer specified string: e.g., smart
    meters / dev Class…)
    """

    rid = 17
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class HardwareVersion(Resource):
    """Hardware Version 18 - String, Single, Optional

    Current hardware version of the device
    """

    rid = 18
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class SoftwareVersion(Resource):
    """Software Version 19 - String, Single, Optional

    Current software version of the device (manufacturer specified
    string). On elaborated LwM2M device, SW could be split in 2 parts: a
    firmware one and a higher level software on top.

    Both pieces of Software are together managed by LwM2M Firmware
    Update Object (Object ID 5)
    """

    rid = 19
    operations = R
    type = 'string'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class BatteryStatus(Resource):
    """Battery Status 20 - Integer, Single, Optional

    This value is only valid for the Device Internal Battery if present
    (one Available Power Sources Resource Instance value is 1).

    Battery
    Status  Meaning Description
    0       Normal  The battery is operating normally and not on power.
    1       Charging        The battery is currently charging.
    2       Charge Complete The battery is fully charged and still on
    power.

    3       Damaged The battery has some problem.
    4       Low Battery     The battery is low on charge.
    5       Not Installed   The battery is not installed.
    6       Unknown The battery information is not available.
    """

    rid = 20
    operations = R
    type = 'integer'
    range = '0-6'
    unit = 'N/A'
    mandatory = False
    multiple = False


class MemoryTotal(Resource):
    """Memory Total 21 - Integer, Single, Optional

    Total amount of storage space which can store data and software in
    the LwM2M Device (expressed in kilobytes).
    """

    rid = 21
    operations = R
    type = 'integer'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = False


class ExtDevInfo(Resource):
    """ExtDevInfo 22 - Objlnk, Multiple, Optional

    Reference to external “Device” object instance containing
    information. For example, such an external device can be a Host
    Device, which is a device into which the Device containing the LwM2M
    client is embedded. This Resource may be used to retrieve
    information about the Host Device.
    """

    rid = 22
    operations = R
    type = 'objlnk'
    range = 'N/A'
    unit = 'N/A'
    mandatory = False
    multiple = True


class Device(ObjectDef):
    """Device Object 3 - Mandatory, Single

    This LwM2M Object provides a range of device related information
    which can be queried by the LwM2M Server, and a device reboot and
    factory reset function.
    """

    oid = 3
    mandatory = True
    multiple = False

    # ID=0, String, R, Single, Optional, range: N/A, unit: N/A
    manufacturer = Manufacturer()

    # ID=1, String, R, Single, Optional, range: N/A, unit: N/A
    model_number = ModelNumber()

    # ID=2, String, R, Single, Optional, range: N/A, unit: N/A
    serial_number = SerialNumber()

    # ID=3, String, R, Single, Optional, range: N/A, unit: N/A
    firmware_version = FirmwareVersion()

    # ID=4, N/a, E, Single, Mandatory, range: N/A, unit: N/A
    reboot = Reboot()

    # ID=5, N/a, E, Single, Optional, range: N/A, unit: N/A
    factory_reset = FactoryReset()

    # ID=6, Integer, R, Multiple, Optional, range: 0-7, unit: N/A
    available_power_sources = AvailablePowerSources()

    # ID=7, Integer, R, Multiple, Optional, range: N/A, unit: mV
    power_source_voltage = PowerSourceVoltage()

    # ID=8, Integer, R, Multiple, Optional, range: N/A, unit: mA
    power_source_current = PowerSourceCurrent()

    # ID=9, Integer, R, Single, Optional, range: 0-100, unit: %
    battery_level = BatteryLevel()

    # ID=10, Integer, R, Single, Optional, range: N/A, unit: KB
    memory_free = MemoryFree()

    # ID=11, Integer, R, Multiple, Mandatory, range: 0-8, unit: N/A
    error_code = ErrorCode()

    # ID=12, N/a, E, Single, Optional, range: N/A, unit: N/A
    reset_error_code = ResetErrorCode()

    # ID=13, Time, RW, Single, Optional, range: N/A, unit: N/A
    current_time = CurrentTime()

    # ID=14, String, RW, Single, Optional, range: N/A, unit: N/A
    utc_offset = UTCOffset()

    # ID=15, String, RW, Single, Optional, range: N/A, unit: N/A
    timezone = Timezone()

    # ID=16, String, R, Single, Mandatory, range: N/A, unit: N/A
    supported_binding_and_modes = SupportedBindingAndModes()

    # ID=17, String, R, Single, Optional, range: N/A, unit: N/A
    device_type = DeviceType()

    # ID=18, String, R, Single, Optional, range: N/A, unit: N/A
    hardware_version = HardwareVersion()

    # ID=19, String, R, Single, Optional, range: N/A, unit: N/A
    software_version = SoftwareVersion()

    # ID=20, Integer, R, Single, Optional, range: 0-6, unit: N/A
    battery_status = BatteryStatus()

    # ID=21, Integer, R, Single, Optional, range: N/A, unit: N/A
    memory_total = MemoryTotal()

    # ID=22, Objlnk, R, Multiple, Optional, range: N/A, unit: N/A
    extdevinfo = ExtDevInfo()