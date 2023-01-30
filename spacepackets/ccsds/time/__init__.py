"""This module contains the CCSDS specific time code implementations."""
from .common import CcsdsTimeProvider, CcsdsTimeCodeId, SECONDS_PER_DAY, MS_PER_DAY
from .cds import CdsShortTimestamp
