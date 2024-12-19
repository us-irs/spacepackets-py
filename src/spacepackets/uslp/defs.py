class UslpInvalidFrameHeaderError(Exception):
    pass


class UslpInvalidRawPacketOrFrameLenError(Exception):
    pass


class UslpInvalidConstructionRulesError(Exception):
    pass


class UslpFhpVhopFieldMissingError(Exception):
    pass


class UslpTruncatedFrameNotAllowedError(Exception):
    pass


class UslpVersionMissmatchError(Exception):
    pass


class UslpTypeMissmatchError(Exception):
    pass


class UslpChecksumError(Exception):
    pass
