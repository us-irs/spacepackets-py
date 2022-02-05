import enum


class ManagedParamsPhysicalChannelKeys(enum.IntEnum):
    HasInsertZone = 0
    InsertZoneLen = 1


__PHYSICAL_CHANNEL_PARAMS = {
    ManagedParamsPhysicalChannelKeys.HasInsertZone: False,
    ManagedParamsPhysicalChannelKeys.InsertZoneLen: 0,
}


def set_insert_zone(enable: bool, len: int):
    """Specify whether USLP transfer frame for a given physical channel has an insert zone
    and how long it is"""
    __PHYSICAL_CHANNEL_PARAMS[ManagedParamsPhysicalChannelKeys.HasInsertZone] = enable
    __PHYSICAL_CHANNEL_PARAMS[ManagedParamsPhysicalChannelKeys.InsertZoneLen] = len
