import enum


class Subservice(enum.IntEnum):
    TM_INFO_EVENT = 1
    TM_LOW_SEVERITY_EVENT = 2
    TM_MEDIUM_SEVERITY_EVENT = 3
    TM_HIGH_SEVERITY_EVENT = 4
    TC_ENABLE_EVENT_REPORTING = 5
    TC_DISABLE_EVENT_REPORTING = 6
