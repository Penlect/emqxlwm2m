"""Generated by emqxlwm2m.codegen at 2020-11-22 12:13:49

LwM2M Object: Connectivity Statistics
ID: 7, URN: urn:oma:lwm2m:oma:7, Optional, Single
"""

from emqxlwm2m.lwm2m import *


class SMSTxCounter(Resource):
    """SMS Tx Counter 0 - Integer, Single, Optional

    Indicate the total number of SMS successfully transmitted during the
    collection period.
    """

    rid = 0
    operations = R
    type = "integer"
    range = "N/A"
    unit = "N/A"
    mandatory = False
    multiple = False


class SMSRxCounter(Resource):
    """SMS Rx Counter 1 - Integer, Single, Optional

    Indicate the total number of SMS successfully received during the
    collection period.
    """

    rid = 1
    operations = R
    type = "integer"
    range = "N/A"
    unit = "N/A"
    mandatory = False
    multiple = False


class TxData(Resource):
    """Tx Data 2 - Integer, Single, Optional

    Indicate the total amount of IP data transmitted during the
    collection period.
    """

    rid = 2
    operations = R
    type = "integer"
    range = "N/A"
    unit = "Kilo-Bytes"
    mandatory = False
    multiple = False


class RxData(Resource):
    """Rx Data 3 - Integer, Single, Optional

    Indicate the total amount of IP data received during the collection
    period.
    """

    rid = 3
    operations = R
    type = "integer"
    range = "N/A"
    unit = "Kilo-Bytes"
    mandatory = False
    multiple = False


class MaxMessageSize(Resource):
    """Max Message Size 4 - Integer, Single, Optional

    The maximum IP message size that is used during the collection
    period.
    """

    rid = 4
    operations = R
    type = "integer"
    range = "N/A"
    unit = "Byte"
    mandatory = False
    multiple = False


class AverageMessageSize(Resource):
    """Average Message Size 5 - Integer, Single, Optional

    The average IP message size that is used during the collection
    period.
    """

    rid = 5
    operations = R
    type = "integer"
    range = "N/A"
    unit = "Byte"
    mandatory = False
    multiple = False


class Start(Resource):
    """Start 6 - N/a, Single, Mandatory

    Reset resources 0-5 to 0 and start to collect information, If
    resource 8 (Collection Period) value is 0, the client will keep
    collecting information until resource 7 (Stop) is executed,
    otherwise the client will stop collecting information after
    specified period ended.

            Note:When reporting the Tx Data or Rx Data, the LwM2M Client
    reports the total KB transmitted/received over IP bearer(s),
    including all protocol header bytes up to and including the IP
    header. This does not include lower level
    retransmissions/optimizations (e.g. RAN, header compression) or SMS
    messages.
    """

    rid = 6
    operations = E
    type = "N/A"
    range = "N/A"
    unit = "N/A"
    mandatory = True
    multiple = False


class Stop(Resource):
    """Stop 7 - N/a, Single, Mandatory

    Stop collecting information, but do not reset resources 0-5.
    """

    rid = 7
    operations = E
    type = "N/A"
    range = "N/A"
    unit = "N/A"
    mandatory = True
    multiple = False


class CollectionPeriod(Resource):
    """Collection Period 8 - Integer, Single, Optional

    The default collection period in seconds. The value 0 indicates that
    the collection period is not set.
    """

    rid = 8
    operations = RW
    type = "integer"
    range = "N/A"
    unit = "Seconds"
    mandatory = False
    multiple = False


class ConnectivityStatistics(ObjectDef):
    """Connectivity Statistics Object 7 - Optional, Single

    This LwM2M Objects enables client to collect statistical information
    and enables the LwM2M Server to retrieve these information, set the
    collection duration and reset the statistical parameters.
    """

    oid = 7
    mandatory = False
    multiple = False

    # ID=0, Integer, R, Single, Optional, range: N/A, unit: N/A
    sms_tx_counter = SMSTxCounter()

    # ID=1, Integer, R, Single, Optional, range: N/A, unit: N/A
    sms_rx_counter = SMSRxCounter()

    # ID=2, Integer, R, Single, Optional, range: N/A, unit: Kilo-Bytes
    tx_data = TxData()

    # ID=3, Integer, R, Single, Optional, range: N/A, unit: Kilo-Bytes
    rx_data = RxData()

    # ID=4, Integer, R, Single, Optional, range: N/A, unit: Byte
    max_message_size = MaxMessageSize()

    # ID=5, Integer, R, Single, Optional, range: N/A, unit: Byte
    average_message_size = AverageMessageSize()

    # ID=6, N/a, E, Single, Mandatory, range: N/A, unit: N/A
    start = Start()

    # ID=7, N/a, E, Single, Mandatory, range: N/A, unit: N/A
    stop = Stop()

    # ID=8, Integer, RW, Single, Optional, range: N/A, unit: Seconds
    collection_period = CollectionPeriod()
