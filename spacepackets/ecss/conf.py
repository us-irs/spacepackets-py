import enum


class PusVersion(enum.IntEnum):
    PUS_A = 0,
    PUS_C = 1,
    UNKNOWN = 99


class EcssConfKeys(enum.IntEnum):
    ECSS_APID = 0,
    PUS_TM_TYPE = 1,
    PUS_TC_TYPE = 2,
    ECSS_TM_APID = 3


ECSS_DICT = {
    EcssConfKeys.ECSS_APID: 0xef,
    EcssConfKeys.PUS_TM_TYPE: PusVersion.PUS_C,
    EcssConfKeys.PUS_TC_TYPE: PusVersion.PUS_C,
    EcssConfKeys.ECSS_TM_APID: 0xef
}


def set_default_apid(default_apid: int):
    ECSS_DICT[EcssConfKeys.ECSS_APID] = default_apid


def get_default_apid() -> int:
    return ECSS_DICT[EcssConfKeys.ECSS_APID]


def set_pus_tc_version(pus_type: PusVersion):
    ECSS_DICT[EcssConfKeys.PUS_TC_TYPE] = pus_type


def get_pus_tc_version() -> PusVersion:
    return ECSS_DICT[EcssConfKeys.PUS_TC_TYPE]


def set_pus_tm_version(pus_type: PusVersion):
    ECSS_DICT[EcssConfKeys.PUS_TM_TYPE] = pus_type


def get_pus_tm_version() -> PusVersion:
    return ECSS_DICT[EcssConfKeys.PUS_TM_TYPE]


def insert_tm_apid(tm_apid: int):
    ECSS_DICT[EcssConfKeys.ECSS_TM_APID] = tm_apid


def get_tm_apid() -> int:
    return ECSS_DICT[EcssConfKeys.ECSS_TM_APID]
