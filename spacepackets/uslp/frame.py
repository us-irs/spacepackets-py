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
from .defs import (
    UslpInvalidRawPacketOrFrameLen,
    UslpTruncatedFrameNotAllowed,
    UslpInvalidConstructionRules,
    UslpInvalidFrameHeader,
    UslpFhpVhopFieldMissing,
)

from typing import Union, Optional

FrameHeaderT = Union[TruncatedPrimaryHeader, PrimaryHeader]

USLP_TFDF_MAX_SIZE = 65529


class InsertZoneProperties:
    def __init__(self, present: bool, size: int):
        self.present = present
        self.size = size


class FecfProperties:
    def __init__(self, present: bool, size: int):
        self.present = present
        self.size = size


class FramePropertiesBase:
    def __init__(
        self,
        has_insert_zone: bool,
        has_fecf: bool,
        insert_zone_len: Optional[int] = None,
        fecf_len: Optional[int] = None,
    ):
        if has_insert_zone and insert_zone_len is None:
            raise ValueError
        if has_fecf and fecf_len is None:
            raise ValueError
        self.insert_zone_properties = InsertZoneProperties(
            present=has_insert_zone, size=insert_zone_len
        )
        self.fecf_properties = FecfProperties(present=has_fecf, size=fecf_len)


class FixedFrameProperties(FramePropertiesBase):
    def __init__(
        self,
        fixed_len: int,
        has_insert_zone: bool,
        has_fecf: bool,
        insert_zone_len: Optional[int] = None,
        fecf_len: Optional[int] = None,
    ):
        """Contains properties required when unpacking fixed USLP frames. These properties
        can not be determined by parsing the frame. The standard refers to these properties
        as managed parameters.
        :param has_insert_zone:
        :param has_fecf:
        :param insert_zone_len:
        :param fecf_len:
        """
        super().__init__(
            has_insert_zone=has_insert_zone,
            has_fecf=has_fecf,
            insert_zone_len=insert_zone_len,
            fecf_len=fecf_len,
        )
        self.fixed_len = fixed_len


class VarFrameProperties(FramePropertiesBase):
    def __init__(
        self,
        has_insert_zone: bool,
        has_fecf: bool,
        truncated_frame_len: int,
        insert_zone_len: Optional[int] = None,
        fecf_len: Optional[int] = None,
    ):
        """Contains properties required when unpacking variable USLP frames. These properties
        can not be determined by parsing the frame. The standard refers to these properties
        as managed parameters.
        :param has_insert_zone:
        :param insert_zone_len:
        :param has_fecf:
        :param fecf_len:
        :param truncated_frame_len:
        """
        super().__init__(
            has_insert_zone=has_insert_zone,
            has_fecf=has_fecf,
            insert_zone_len=insert_zone_len,
            fecf_len=fecf_len,
        )
        self.truncated_frame_len = truncated_frame_len


FramePropertiesT = Union[FixedFrameProperties, VarFrameProperties]
UslpHeaderT = Union[TruncatedPrimaryHeader, PrimaryHeader]


class TfdzConstructionRules(enum.IntEnum):
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
        tfdz_cnstr_rules: TfdzConstructionRules,
        uslp_ident: UslpProtocolIdentifier,
        tfdz: bytes,
        fhp_or_lvop: Optional[int] = None,
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
        The FHP/LVOP field is only required when the frame type is set to a fixed length.
        :param tfdz_cnstr_rules: 3 bits, identifies how the protocol organizes data within the TFDZ
            in order to transport it.
        :param uslp_ident: 5 bits, Identifies the CCSDS recognized protocol,
            procedure, or type of data contained within the TFDZ.
        :param tfdz: Transfer Frame Data Zone
        :param fhp_or_lvop: Optional First Header Pointer or Last Valid Octet Pointer.
        :raises ValueError: TFDZ too large
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

    def pack(
        self, truncated: bool = False, frame_type: Optional[FrameType] = None
    ) -> bytearray:
        packet = bytearray()
        packet.append(self.tfdz_contr_rules << 5 | self.uslp_ident)
        if frame_type is None:
            # Auto-determine frame type from construction rule
            if self.__cnstr_rules_for_fp():
                frame_type = FrameType.FIXED
            elif self.__cnstr_rules_for_vp():
                frame_type = FrameType.VARIABLE
        if self.should_have_fhp_or_lvp_field(
            truncated=truncated, frame_type=frame_type
        ):
            if self.fhp_or_lvop is None:
                raise UslpFhpVhopFieldMissing
            packet.extend(struct.pack("!H", self.fhp_or_lvop))
        packet.extend(self.tfdz)
        return packet

    def should_have_fhp_or_lvp_field(
        self, truncated: bool, frame_type: Optional[FrameType]
    ) -> bool:
        if frame_type is not None and frame_type == FrameType.VARIABLE:
            return False
        if not truncated and self.tfdz_contr_rules in [
            TfdzConstructionRules.FpPacketSpanningMultipleFrames,
            TfdzConstructionRules.FpContinuingPortionOfMapaSDU,
            TfdzConstructionRules.FpFixedStartOfMapaSDU,
        ]:
            return True
        return False

    def verify_frame_type(self, frame_type: FrameType) -> bool:
        if frame_type == FrameType.FIXED and self.__cnstr_rules_for_fp():
            return True
        elif frame_type == FrameType.VARIABLE and self.__cnstr_rules_for_vp():
            return True
        return False

    def __cnstr_rules_for_fp(self) -> bool:
        if self.tfdz_contr_rules in [
            TfdzConstructionRules.FpPacketSpanningMultipleFrames,
            TfdzConstructionRules.FpContinuingPortionOfMapaSDU,
            TfdzConstructionRules.FpFixedStartOfMapaSDU,
        ]:
            return True
        return False

    def __cnstr_rules_for_vp(self) -> bool:
        if self.tfdz_contr_rules in [
            TfdzConstructionRules.VpContinuingSegment,
            TfdzConstructionRules.VpLastSegment,
            TfdzConstructionRules.VpOctetStream,
            TfdzConstructionRules.VpNoSegmentation,
            TfdzConstructionRules.VpStartingSegment,
        ]:
            return True
        return False

    @classmethod
    def __empty(cls) -> TransferFrameDataField:
        empty = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.FpPacketSpanningMultipleFrames,
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
        """Unpack a TFDF, given a raw bytearray.

        :param raw_tfdf:
        :param truncated: Required to determine whether a TFDF has a FHP or LVOP field
        :param exact_len: Exact length of the TFDP. Needs to be determined externally because
            the length information of a packet is usually fixed or part of the USLP primary header
            and can not be determined from the TFDP field alone
        :param frame_type: Can be passed optionally to verify whether the construction rules are
            valid for the given frame type
        :return:
        """
        tfdf = cls.__empty()
        if len(raw_tfdf) < 1:
            raise UslpInvalidRawPacketOrFrameLen
        tfdf.tfdz_contr_rules = (raw_tfdf[0] >> 5) & 0b111
        tfdf.uslp_ident = raw_tfdf[0] & 0b11111
        if frame_type is not None:
            if not tfdf.verify_frame_type(frame_type=frame_type):
                raise UslpInvalidConstructionRules
        if tfdf.should_have_fhp_or_lvp_field(
            truncated=truncated, frame_type=frame_type
        ):
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
        insert_zone: Optional[bytes] = None,
        op_ctrl_field: Optional[bytes] = None,
        fecf: Optional[bytes] = None,
    ):
        self.header = header
        self.tfdf = tfdf
        self.insert_zone = insert_zone
        self.op_ctrl_field = op_ctrl_field
        self.fecf = fecf

    def pack(
        self, truncated: bool = False, frame_type: Optional[FrameType] = None
    ) -> bytearray:
        frame = bytearray()
        frame.extend(self.header.pack())
        if self.insert_zone is not None:
            frame.extend(self.insert_zone)
        frame.extend(self.tfdf.pack(truncated=truncated, frame_type=frame_type))
        if self.op_ctrl_field:
            if not self.header.op_ctrl_flag:
                raise UslpInvalidFrameHeader
            if len(self.op_ctrl_field) != 4:
                raise ValueError
            frame.extend(self.op_ctrl_field)
        else:
            if not truncated and self.header.op_ctrl_flag:
                raise UslpInvalidFrameHeader
        if self.fecf is not None:
            frame.extend(self.fecf)
        return frame

    def set_frame_len_in_header(self):
        # According to the standard, the frame length field will contain the length of of the
        # frame minus 1. Also check whether this is a regular header and not a truncated one,
        # as the truncated one does not have the frame length field
        if isinstance(self.header, PrimaryHeader):
            self.header.frame_len = self.len() - 1

    def len(self):
        size = self.header.len() + self.tfdf.len()
        if self.insert_zone is not None:
            size += len(self.insert_zone)
        if self.op_ctrl_field is not None:
            size += len(self.op_ctrl_field)
        if self.fecf is not None:
            size += len(self.fecf)
        return size

    @classmethod
    def __empty(cls) -> TransferFrame:
        empty_header = TruncatedPrimaryHeader(
            scid=0, src_dest=SourceOrDestField.SOURCE, map_id=0, vcid=0
        )
        empty_data_field = TransferFrameDataField(
            tfdz_cnstr_rules=TfdzConstructionRules.FpPacketSpanningMultipleFrames,
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
    def unpack(  # noqa: C901
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
            raise UslpInvalidRawPacketOrFrameLen
        if frame_type == FrameType.FIXED:
            if not isinstance(frame_properties, FixedFrameProperties):
                raise ValueError
            if len(raw_frame) < frame_properties.fixed_len:
                raise UslpInvalidRawPacketOrFrameLen
        header_type = determine_header_type(header_start=raw_frame)
        if header_type == HeaderType.TRUNCATED:
            # Truncated frames are only allowed if the frame type is specified as variable
            # as specified by the standard on page p.161
            if frame_type != FrameType.VARIABLE:
                raise UslpTruncatedFrameNotAllowed
            frame.header = TruncatedPrimaryHeader.unpack(raw_packet=raw_frame)
        else:
            frame.header = PrimaryHeader.unpack(raw_packet=raw_frame)
        header_len = frame.header.len()
        if frame_type == FrameType.FIXED and (
            frame.header.frame_len + 1 != frame_properties.fixed_len
        ):
            raise UslpInvalidRawPacketOrFrameLen
        exact_tfdf_len = cls.__get_tfdf_len(
            frame_type=frame_type,
            header_type=header_type,
            raw_frame_len=len(raw_frame),
            header=frame.header,
            properties=frame_properties,
        )
        if exact_tfdf_len <= 0 or header_len + exact_tfdf_len > len(raw_frame):
            raise UslpInvalidRawPacketOrFrameLen
        current_idx = header_len
        # Skip insert zone if present
        if frame_properties.insert_zone_properties.present:
            if (
                header_len
                + frame_properties.insert_zone_properties.size
                + exact_tfdf_len
                > len(raw_frame)
            ):
                raise UslpInvalidRawPacketOrFrameLen
            frame.insert_zone = raw_frame[
                current_idx : current_idx + frame_properties.insert_zone_properties.size
            ]
            current_idx += frame_properties.insert_zone_properties.size
        # Parse the Transfer Frame Data Field
        frame.tfdf = TransferFrameDataField.unpack(
            frame_type=frame_type,
            truncated=frame.header.truncated(),
            raw_tfdf=raw_frame[current_idx:],
            exact_len=exact_tfdf_len,
        )
        current_idx += exact_tfdf_len
        # Parse OCF field if present
        if not header_type == HeaderType.TRUNCATED and frame.header.op_ctrl_flag:
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
        # Truncated frames are not allowed if the frame type is specified as fixed.
        # This check was already performed so it does not need to be done again.
        if frame_type == FrameType.FIXED:
            # According to standard, the length count C equals one fewer than the total octets in
            # the transfer frame.
            exact_tfdf_len = header.frame_len + 1 - header_len
            if raw_frame_len < exact_tfdf_len:
                raise UslpInvalidRawPacketOrFrameLen
        else:
            # Truncated frames are only allowed if the frame type is Variable. The truncated
            # frame length is then a managed parameter for a specific virtual channel.
            if header_type == HeaderType.TRUNCATED:
                exact_tfdf_len = properties.truncated_frame_len - header_len
            else:
                exact_tfdf_len = header.frame_len + 1 - header_len
        if properties.fecf_properties.present:
            exact_tfdf_len -= properties.fecf_properties.size
        if header_type != HeaderType.TRUNCATED and header.op_ctrl_flag:
            exact_tfdf_len -= 4
        if properties.insert_zone_properties.present:
            exact_tfdf_len -= properties.insert_zone_properties.size
        return exact_tfdf_len
