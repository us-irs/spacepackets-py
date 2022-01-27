import enum
import struct

from .header import TruncatedUslpPrimaryHeader, PrimaryHeader
from typing import Union, Optional


FrameHeaderT = Union[TruncatedUslpPrimaryHeader, PrimaryHeader]

USLP_TFDF_MAX_SIZE = 65529


class TFDZConstructionRules(enum.IntEnum):
    """Values prefixed with FP are applicable to fixed packets, those with VP to variable length
    packets"""

    # Fixed packets
    FpPacketSpanningMultipleFrames = 0b000
    FpFixedStartOfMapaSDU = 0b001
    FpContinuingPortionOfMapaSDU = 0b010
    # Variable packets
    VpOctetStream = 0b011
    VpStartingSegment = 0b100
    VpContinuingSegment = 0b101
    VpLastSegment = 0b110
    VpNoSegmentation = 0b111


class UslpProtocolIdentifier(enum.IntEnum):
    """Also called UPID. Identifies the CCSDS recognized protocol, procedure, or type of data
    contained within the TFDZ. See list here: https://sanaregistry.org/r/uslp_protocol_id/"""

    SPACE_PACKETS_ENCAPSULATION_PACKETS = 0b00000
    COP_1_CTRL_COMMANDS = 0b00001
    COP_2_CTRL_COMMANDS = 0b00010
    SDLS_CTRL_COMMANDS = 0b00011
    USER_DEFINED_OCTET_STREAM = 0b00100
    MISSION_SPECIFIC_INFO_1_MAPA_SDU = 0b00101
    PROXIMITY_1_SPDUS = 0b00111
    IDLE_DATA = 0b11111
    PRIXMITY_1_PSEUDO_PACKET_ID_1 = 0b01000
    PRIXMITY_1_PSEUDO_PACKET_ID_2 = 0b01000


class TransferFrameDataField:
    """USLP transfer frame data field (TFDF). For datailed information, refer to the USLP Blue Book
    CCSDS 732.1-B-2. p.86. The TFDP follows the Primary Header or the Transfer Frame Insert Zone,
    if present.

    The data field has a header varying from 1 to 3 bytes as well.
    """

    def __init__(
        self,
        tfdz_cnstr_rules: TFDZConstructionRules,
        uslp_ident: UslpProtocolIdentifier,
        tfdz: bytes,
        fhp_or_lvop: Optional[int],
    ):
        """
        Notes on the FHP or LVOP field. For more details, refer to CCSDS 732.1-B-2. p.92:
         - If the TFDZ construction rule is equal to '000' (TFDZ spanning multiple frames), this
           field is designated as FHP. It then contains the offset within the TFDZ to the first
           octet of the first packet header. If no packet starts nor ends
           within the TFDZ, this field is set to all ones.
           Its purpose is to delimit variable-length packets contained within the TFDZ, by
           pointing directly to the location of the first packet from which its length can be
           determined. The location of any subsequent packets are determined by using the length
           field of those packets.
         - If the TFDZ constructions rule is equal to '001' or '010', this field is designated as
           LVOP and contains tbe offset to the last octet of the MAPA_SDU being transferred, with
           the remaining octets composed of a project specific idle data pattern. If the MAPA_SDU
           does not complete within this fixed-length TFDZ, then the value contained within the LVOP
           shall be set to binary all ones.
        :param tfdz_cnstr_rules: 3 bits, identifies how the protocol organizes data within the TFDZ
            in order to transport it.
        :param uslp_ident: 5 bits, Identifies the CCSDS recognized protocol,
            procedure, or type of data contained within the TFDZ.
        :param tfdz: Transfer Frame Data Zone
        :param fhp_or_lvop: Optional First Header Pointer or Last Valid Octet Pointer.
        :raises ValueErrror: TFDZ too large
        """
        self.tfdz_contr_rules = tfdz_cnstr_rules
        self.uslp_ident = uslp_ident
        self.fhp_or_lvop = fhp_or_lvop

        self.tfdz = tfdz
        allowed_max_len = USLP_TFDF_MAX_SIZE - self.header_len()
        if len(tfdz) > allowed_max_len:
            raise ValueError
        self.size += len(tfdz)

    @property
    def tfdz(self):
        return self._tfdz

    @tfdz.setter
    def tfdz(self, tfdz: bytes):
        self._tfdz = tfdz
        self.size = self.header_len() + len(tfdz)

    def header_len(self) -> int:
        return 1 if self.fhp_or_lvop is None else 3

    def len(self):
        return self.header_len() + len(self.tfdz)

    def pack(self) -> bytearray:
        packet = bytearray()
        packet.append(self.tfdz_contr_rules << 5 | self.uslp_ident)
        if self.fhp_or_lvop is not None:
            packet.extend(struct.pack("!H", self.fhp_or_lvop))
        packet.extend(self.tfdz)
        return packet


class TransferFrame:
    """Refer to CCSDS 732.1-B-2. p.77 for detailed information on the frame format. This is the
    format without the SDLS option"""

    def __init__(
        self,
        header: FrameHeaderT,
        tfdf: TransferFrameDataField,
        insert_zone: Optional[bytes],
        op_ctrl_field: Optional[bytes],
        fecf: Optional[int],
    ):
        self.header = header
        self.tfdf = tfdf
        self.insert_zone = insert_zone
        if len(op_ctrl_field) != 4:
            raise ValueError
        self.op_ctrl_field = op_ctrl_field
        self.fecf = fecf

    def pack(self) -> bytearray:
        frame = bytearray()
        frame.extend(self.header.pack())
        if self.insert_zone is not None:
            frame.extend(self.insert_zone)
        frame.extend(self.tfdf.pack())
        if self.op_ctrl_field is not None:
            frame.extend(self.op_ctrl_field)
        if self.fecf is not None:
            frame.extend(struct.pack("!I", self.fecf))
        return frame
