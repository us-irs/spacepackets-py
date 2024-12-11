from __future__ import annotations

import enum


class TlvType(enum.IntEnum):
    """All available TLV types"""

    FILESTORE_REQUEST = 0x00
    FILESTORE_RESPONSE = 0x01
    MESSAGE_TO_USER = 0x02
    FAULT_HANDLER = 0x04
    FLOW_LABEL = 0x05
    ENTITY_ID = 0x06


class FilestoreActionCode(enum.IntEnum):
    """All filestore action codes as specified in CCSDS 727.0-B-5 p.86
    SNP: Second name present, SNN: Second name not present"""

    CREATE_FILE_SNM = 0b0000
    DELETE_FILE_SNN = 0b0001
    RENAME_FILE_SNP = 0b0010
    APPEND_FILE_SNP = 0b0011
    REPLACE_FILE_SNP = 0b0100
    CREATE_DIR_SNN = 0b0101
    REMOVE_DIR_SNN = 0b0110
    DENY_FILE_SMM = 0b0111
    DENY_DIR_SNN = 0b1000


class FilestoreResponseStatusCode(enum.IntEnum):
    """File store response status codes. First four bits are the action code, last four bits
    the status code"""

    SUCCESS = 0b0000
    NOT_PERFORMED = 0b1111
    APPEND_FROM_DATA_FILE_NOT_EXISTS = 0b0010

    CREATE_SUCCESS = FilestoreActionCode.CREATE_FILE_SNM << 4 | SUCCESS
    CREATE_NOT_ALLOWED = FilestoreActionCode.CREATE_FILE_SNM << 4 | 0b0001
    CREATE_NOT_PERFORMED = FilestoreActionCode.CREATE_FILE_SNM << 4 | NOT_PERFORMED

    DELETE_SUCCESS = FilestoreActionCode.DELETE_FILE_SNN << 4 | SUCCESS
    DELETE_FILE_DOES_NOT_EXIST = FilestoreActionCode.DELETE_FILE_SNN << 4 | 0b0001
    DELETE_NOT_ALLOWED = FilestoreActionCode.DELETE_FILE_SNN << 4 | NOT_PERFORMED

    RENAME_SUCCESS = FilestoreActionCode.RENAME_FILE_SNP << 4 | SUCCESS
    RENAME_OLD_FILE_DOES_NOT_EXIST = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0001
    RENAME_NEW_FILE_DOES_EXIST = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0010
    RENAME_NOT_ALLOWED = FilestoreActionCode.RENAME_FILE_SNP << 4 | 0b0011
    RENAME_NOT_PERFORMED = FilestoreActionCode.RENAME_FILE_SNP << 4 | NOT_PERFORMED

    APPEND_SUCCESS = FilestoreActionCode.APPEND_FILE_SNP << 4 | SUCCESS
    # Name of file whose contents form the first part of the new file and name of the new file
    APPEND_FILE_NAME_ONE_NOT_EXISTS = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0001
    # Name of the file whose contents will form the second part of the new file
    APPEND_FILE_NAME_TWO_NOT_EXISTS = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0010
    APPEND_NOT_ALLOWED = FilestoreActionCode.APPEND_FILE_SNP << 4 | 0b0011
    APPEND_NOT_PERFORMED = FilestoreActionCode.APPEND_FILE_SNP << 4 | NOT_PERFORMED

    REPLACE_SUCCESS = FilestoreActionCode.REPLACE_FILE_SNP << 4 | SUCCESS
    # File name
    REPLACE_FILE_NAME_ONE_TO_BE_REPLACED_DOES_NOT_EXIST = (
        FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0001
    )
    REPLACE_FILE_NAME_TWO_REPLACE_SOURCE_NOT_EXIST = (
        FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0010
    )
    REPLACE_NOT_ALLOWED = FilestoreActionCode.REPLACE_FILE_SNP << 4 | 0b0011
    REPLACE_NOT_PERFORMED = FilestoreActionCode.REPLACE_FILE_SNP << 4 | NOT_PERFORMED

    CREATE_DIR_SUCCESS = FilestoreActionCode.CREATE_DIR_SNN << 4 | SUCCESS
    CREATE_DIR_CAN_NOT_BE_CREATED = FilestoreActionCode.CREATE_DIR_SNN << 4 | 0b0001
    CREATE_DIR_NOT_PERFORMED = FilestoreActionCode.CREATE_DIR_SNN << 4 | NOT_PERFORMED

    REMOVE_DIR_SUCCESS = FilestoreActionCode.REMOVE_DIR_SNN << 4 | SUCCESS
    REMOVE_DIR_DOES_NOT_EXIST = FilestoreActionCode.REMOVE_DIR_SNN << 4 | 0b0001
    REMOVE_DIR_NOT_ALLOWED = FilestoreActionCode.REMOVE_DIR_SNN << 4 | 0b0010
    REMOVE_DIR_NOT_PERFORMED = FilestoreActionCode.REMOVE_DIR_SNN << 4 | NOT_PERFORMED

    DENY_FILE_DEL_SUCCESS = FilestoreActionCode.DENY_FILE_SMM << 4 | SUCCESS
    DENY_FILE_DEL_NOT_ALLOWED = FilestoreActionCode.DENY_FILE_SMM << 4 | 0b0010
    DENY_FILE_DEL_NOT_PERFORMED = FilestoreActionCode.DENY_FILE_SMM << 4 | NOT_PERFORMED

    DENY_DIR_DEL_SUCCESS = FilestoreActionCode.DENY_DIR_SNN << 4 | SUCCESS
    DENY_DIR_DEL_NOT_ALLOWED = FilestoreActionCode.DENY_DIR_SNN << 4 | 0b0010
    DENY_DIR_DEL_NOT_PERFORMED = FilestoreActionCode.DENY_DIR_SNN << 4 | NOT_PERFORMED
    INVALID = -1


class ProxyMessageType(enum.IntEnum):
    PUT_REQUEST = 0x00
    MSG_TO_USER = 0x01
    FS_REQUEST = 0x02
    FAULT_HANDLER_OVERRIDE = 0x03
    TRANSMISSION_MODE = 0x04
    FLOW_LABEL = 0x05
    SEGMENTATION_CTRL = 0x06
    PUT_RESPONSE = 0x07
    FS_RESPONSE = 0x08
    PUT_CANCEL = 0x09
    CLOSURE_REQUEST = 0x0B


ORIGINATING_TRANSACTION_ID_MSG_TYPE_ID = 0x0A


class DirectoryOperationMessageType(enum.IntEnum):
    LISTING_REQUEST = 0x10
    LISTING_RESPONSE = 0x11
    CUSTOM_LISTING_PARAMETERS = 0x15
    """Custom message type not specified by the standard. Used to supply parameters like the
    recursive and the all option to the directory listing."""


class TlvTypeMissmatchError(Exception):
    def __init__(self, found: TlvType, expected: TlvType):
        self.found = found
        self.expected = expected
        super().__init__(f"Expected TLV {self.expected}, found {self.found}")
