import enum


class Severity(enum.IntEnum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4


class Subservice(enum.IntEnum):
    TM_INFO_EVENT = Severity.INFO
    TM_LOW_SEVERITY_EVENT = Severity.LOW
    TM_MEDIUM_SEVERITY_EVENT = Severity.MEDIUM
    TM_HIGH_SEVERITY_EVENT = Severity.HIGH
    TC_ENABLE_EVENT_REPORTING = 5
    TC_DISABLE_EVENT_REPORTING = 6
