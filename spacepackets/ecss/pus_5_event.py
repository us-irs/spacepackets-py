import enum
from warnings import warn


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


class Subservices(Subservice):
    def __init_subclass__(cls, **kwargs):
        """This throws a deprecation warning on subclassing."""
        warn(f"{cls.__name__} will be deprecated.", DeprecationWarning, stacklevel=2)
        super().__init_subclass__(**kwargs)

    def __init__(self, *args, **kwargs):
        """This throws a deprecation warning on initialization."""
        warn(
            f"{self.__class__.__name__} will be deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
