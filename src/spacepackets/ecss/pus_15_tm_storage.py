import enum


class MessageSubtype(enum.IntEnum):
    RETRIEVAL_BY_TIME_RANGE = 9
    DELETE_UP_TO = 11
