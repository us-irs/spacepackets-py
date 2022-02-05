from __future__ import annotations
import enum
import struct

from .header import (
    TruncatedPrimaryHeader,
    PrimaryHeader,
    SourceOrDestField,
    determine_header_type,
    HeaderType,
)
from typing import Union, Optional

FrameHeaderT = Union[TruncatedPrimaryHeader, PrimaryHeader]

USLP_TFDF_MAX_SIZE = 65529


class UslpInvalidRawFrameLen(Exception):
    pass


class UslpInvalidConstructionRules(Exception):
    pass


class UslpTruncatedFrameNotAllowed(Exception):
    pass


class InsertZoneProperties:
    def __init__(self, present: bool, size: int):
        self.present = (present,)
        self.size = size


class FecfProperties:
    def __init__(self, present: bool, size: int):
        self.present = (present,)
        self.size = size


class FramePropertiesBase:
    def __init__(
        self, has_insert_zone: bool, insert_zone_len: int, has_fecf: bool, fecf_len: int
    ):
        self.insert_zone_properties = InsertZoneProperties(
            present=has_insert_zone, size=insert_zone_len
        )
        self.fecf_properties = FecfProperties(present=has_fecf, size=fecf_len)


class FixedFrameProperties(FramePropertiesBase):
    def __init__(
        self, has_insert_zone: bool, insert_zone_len: int, has_fecf: bool, fecf_len: int
    ):
        super().__init__(has_insert_zone, insert_zone_len, has_fecf, fecf_len)
        self.fixed_len = 0


class VarFrameProperties(FramePropertiesBase):
    def __init__(
        self,
        has_insert_zone: bool,
        insert_zone_len: int,
        has_fecf: bool,
        fecf_len: int,
        truncated_frame_len: int,
    ):
        super().__init__(has_insert_zone, insert_zone_len, has_fecf, fecf_len)
        self.truncated_frame_len = truncated_frame_len


FramePropertiesT = Union[FixedFrameProperties, VarFrameProperties]
UslpHeaderT = Union[TruncatedPrimaryHeader, PrimaryHeader]


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
    PRIXMITY_1_PSEUDO_PACKET_ID_1 = 0b00110
    PRIXMITY_1_PSEUDO_PACKET_ID_2 = 0b01000


class FrameType(enum.Enum):
    FIXED = 0
    VARIABLE = 1


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

        self._size = 0
        self.tfdz = tfdz
        allowed_max_len = USLP_TFDF_MAX_SIZE - self.header_len()
        if self.len() > allowed_max_len:
            raise ValueError

    @property
    def tfdz(self):
        return self._tfdz

    @tfdz.setter
    def tfdz(self, tfdz: bytes):
        self._tfdz = tfdz
        self._size = self.header_len() + len(tfdz)

    def header_len(self) -> int:
        return 1 if self.fhp_or_lvop is None else 3

    def len(self):
        return self._size

    def pack(self) -> bytearray:
        packet = bytearray()
        packet.append(self.tfdz_contr_rules << 5 | self.uslp_ident)
        if self.fhp_or_lvop is not None:
            packet.extend(struct.pack("!H", self.fhp_or_lvop))
        packet.extend(self.tfdz)
        return packet

    def has_fhp_or_lvp_field(self, truncated: bool) -> bool:
        if not truncated and self.tfdz_contr_rules in [
            TFDZConstructionRules.FpPacketSpanningMultipleFrames,
            TFDZConstructionRules.FpContinuingPortionOfMapaSDU,
            TFDZConstructionRules.FpFixedStartOfMapaSDU,
        ]:
            return True
        return False

    def verify_frame_type(self, frame_type: FrameType) -> bool:
        if frame_type == FrameType.FIXED and self.tfdz_contr_rules in [
            TFDZConstructionRules.FpPacketSpanningMultipleFrames,
            TFDZConstructionRules.FpContinuingPortionOfMapaSDU,
            TFDZConstructionRules.FpFixedStartOfMapaSDU,
        ]:
            return True
        if frame_type == FrameType.VARIABLE and self.tfdz_contr_rules in [
            TFDZConstructionRules.VpContinuingSegment,
            TFDZConstructionRules.VpLastSegment,
            TFDZConstructionRules.VpOctetStream,
            TFDZConstructionRules.VpNoSegmentation,
            TFDZConstructionRules.VpStartingSegment,
        ]:
            return True
        return False

    @classmethod
    def __empty(cls) -> TransferFrameDataField:
        empty = TransferFrameDataField(
            tfdz_cnstr_rules=TFDZConstructionRules.FpPacketSpanningMultipleFrames,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            fhp_or_lvop=None,
            tfdz=bytearray(),
        )
        return empty

    @classmethod
    def unpack(
        cls,
        raw_tfdf: bytes,
        truncated: bool,
        exact_len: int,
        frame_type: Optional[FrameType],
    ) -> TransferFrameDataField:
        """Unpack a TFDF, given a raw bytearray

        :param raw_tfdf:
        :param truncated: Required to determine whether TFDF has a FHP or LVOP field
        :param exact_len: Exact length of the TFDP. Needs to be determined externally because
            the length information of a packet is usually fixed or part of the USLP primary header
            and can not be determined from the TFDP field alone
        :param frame_type: Can be passed optionally to verify whether the construction rules are
            valid for the given frame type
        :return:
        """
        tfdf = cls.__empty()
        if len(raw_tfdf) < 1:
            raise UslpInvalidRawFrameLen
        tfdf.tfdz_contr_rules = (raw_tfdf[0] >> 5) & 0b111
        tfdf.uslp_ident = raw_tfdf[0] & 0b11111
        if frame_type is not None:
            if not tfdf.verify_frame_type(frame_type=frame_type):
                raise UslpInvalidConstructionRules
        if tfdf.has_fhp_or_lvp_field(truncated=truncated):
            tfdf.fhp_or_lvop = (raw_tfdf[1] << 8) | raw_tfdf[2]
            tfdz_start = 3
        else:
            tfdz_start = 1
        tfdf.tfdz = raw_tfdf[tfdz_start:exact_len]
        return tfdf


class TransferFrame:
    """Refer to CCSDS 732.1-B-2. p.77 for detailed information on the frame format. This is the
    format without the SDLS option"""

    def __init__(
        self,
        header: FrameHeaderT,
        tfdf: TransferFrameDataField,
        insert_zone: Optional[bytes],
        op_ctrl_field: Optional[bytes],
        fecf: Optional[bytes],
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
            frame.extend(self.fecf)
        return frame

    @classmethod
    def __empty(cls) -> TransferFrame:
        empty_header = TruncatedPrimaryHeader(
            scid=0, src_dest=SourceOrDestField.SOURCE, map_id=0, vcid=0
        )
        empty_data_field = TransferFrameDataField(
            tfdz_cnstr_rules=TFDZConstructionRules.FpPacketSpanningMultipleFrames,
            uslp_ident=UslpProtocolIdentifier.SPACE_PACKETS_ENCAPSULATION_PACKETS,
            fhp_or_lvop=None,
            tfdz=bytearray(),
        )
        empty = TransferFrame(
            header=empty_header,
            tfdf=empty_data_field,
            insert_zone=None,
            op_ctrl_field=None,
            fecf=None,
        )
        return empty

    @classmethod
    def unpack(
        cls, raw_frame: bytes, frame_type: FrameType, frame_properties: FramePropertiesT
    ) -> TransferFrame:
        """Unpack a USLP transfer frame from a raw bytearray. All managed parameters have
        to be passed explicitly.
        :param raw_frame:
        :param frame_type:
        :param frame_properties:
        :raises UslpInvalidRawFrameLen: Passed raw bytearray too short
        :raises UslpTruncatedFrameNotAllowed: Truncated frames only allowed if passed frame type
            is Variable. This is REALLY confusing but specified in the standard p.161 D1.2
        :return:
        """
        frame = cls.__empty()
        if len(raw_frame) < 4:
            raise UslpInvalidRawFrameLen
        if frame_type == FrameType.FIXED:
            if not isinstance(frame_properties, FixedFrameProperties):
                raise ValueError
            if len(raw_frame) < frame_properties.fixed_len:
                raise UslpInvalidRawFrameLen
        header_type = determine_header_type(header_start=raw_frame)
        if header_type == HeaderType.TRUNCATED:
            if frame_type == FrameType.VARIABLE:
                raise UslpTruncatedFrameNotAllowed
            frame.header = TruncatedPrimaryHeader.unpack(raw_packet=raw_frame)
        else:
            frame.header = PrimaryHeader.unpack(raw_packet=raw_frame)
        header_len = frame.header.len()
        exact_tfdf_len = cls.__get_tfdf_len(
            frame_type=frame_type,
            header_type=header_type,
            raw_frame_len=len(raw_frame),
            header=frame.header,
            properties=frame_properties,
        )
        if exact_tfdf_len <= 0:
            raise UslpInvalidRawFrameLen
        current_idx = header_len
        # Skip insert zone if present
        if frame_properties.insert_zone_properties.present:
            current_idx += frame_properties.insert_zone_properties.size
            if len(raw_frame) < current_idx:
                raise UslpInvalidRawFrameLen
        # Parse the Transfer Frame Data Field
        frame.tfdf = TransferFrameDataField.unpack(
            frame_type=frame_type,
            truncated=frame.header.truncated(),
            raw_tfdf=raw_frame[current_idx:],
            exact_len=exact_tfdf_len,
        )
        current_idx += exact_tfdf_len
        # Parse OCF field if present
        if frame.header.op_ctrl_flag:
            frame.op_ctrl_field = raw_frame[current_idx : current_idx + 4]
            current_idx += 4
        # Parse Frame Error Control field if present
        if frame_properties.fecf_properties.present:
            frame.fecf = raw_frame[
                current_idx : current_idx + frame_properties.fecf_properties.size
            ]
            current_idx += frame_properties.fecf_properties.size
        return frame

    @staticmethod
    def __get_tfdf_len(
        frame_type: FrameType,
        header_type: HeaderType,
        raw_frame_len: int,
        header: UslpHeaderT,
        properties: FramePropertiesT,
    ):
        """This helper function calculates the initial value for expected TFDF length and subtracts
        all (optional) fields lengths if they are present
        :param frame_type:
        :param header_type:
        :param raw_frame_len:
        :param header:
        :param properties:
        :return:
        """
        header_len = header.len()
        if frame_type == FrameType.FIXED:
            # According to standard, the length count C equals one fewer than the total octets in
            # the transfer frame
            exact_tfdf_len = header.frame_len + 1 - header_len
            if exact_tfdf_len != properties.fixed_len:
                raise ValueError
            if raw_frame_len < exact_tfdf_len:
                raise UslpInvalidRawFrameLen
            exact_tfdf_len = properties.fixed_len
        else:
            # Truncated frames are only allowed if the frame type is Variable. The truncated
            # frame length is then a managed parameter for a specific virtual channel.
            if header_type == HeaderType.TRUNCATED:
                exact_tfdf_len = properties.truncated_frame_len - header_len
            else:
                exact_tfdf_len = header.frame_len + 1 - header_len
        if properties.fecf_properties.present:
            exact_tfdf_len -= properties.fecf_properties.size
        if header.op_ctrl_flag:
            exact_tfdf_len -= 4
        if properties.insert_zone_properties.present:
            exact_tfdf_len -= properties.insert_zone_properties.size
        return exact_tfdf_len
