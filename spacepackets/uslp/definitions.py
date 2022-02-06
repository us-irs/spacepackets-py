class UslpInvalidFrameHeader(Exception):
    pass


class UslpInvalidRawPacketOrFrameLen(Exception):
    pass


class UslpInvalidConstructionRules(Exception):
    pass


class UslpTruncatedFrameNotAllowed(Exception):
    pass


class UslpVersionMissmatch(Exception):
    pass


class UslpTypeMissmatch(Exception):
    pass
