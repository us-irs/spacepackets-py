from spacepackets import BytesTooShortError


class TmSrcDataTooShortError(BytesTooShortError):
    """Similar to the :py:class:`BytesTooShortError`, but specifies that the source data field
    of the PUS telemetry packet is too short."""

    pass
