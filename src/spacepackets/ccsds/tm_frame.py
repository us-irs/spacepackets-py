from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spacepackets.crc import CRC16_CCITT_FUNC
from spacepackets.exceptions import BytesTooShortError, InvalidCrcCcitt16


@dataclass
class MasterChannelId:
    transfer_frame_version: int
    spacecraft_id: int


@dataclass
class TransferFrameDataFieldStatus:
    secondary_header_flag: bool
    sync_flag: bool
    packet_order_flag: bool
    segment_len_id: int
    first_header_pointer: int

    def pack(self) -> bytes:
        packed = bytearray(2)
        packed[0] = self.secondary_header_flag << 7
        packed[0] = packed[0] | self.sync_flag << 6
        packed[0] = packed[0] | self.packet_order_flag << 5
        packed[0] = packed[0] | self.segment_len_id << 3
        packed[0] = packed[0] | self.first_header_pointer >> 8
        packed[1] = self.first_header_pointer & 0b11111111
        return bytes(packed)

    @classmethod
    def unpack(cls, data: bytes) -> TransferFrameDataFieldStatus:
        if len(data) < 2:
            raise BytesTooShortError(2, len(data))
        return cls(
            bool((data[0] >> 7) & 0b1),
            bool((data[0] >> 6) & 0b1),
            bool((data[0] >> 5) & 0b1),
            (data[0] >> 3) & 0b11,
            ((data[0] & 0b111) << 8) | data[1],
        )


class TmFramePrimaryHeader:
    def __init__(
        self,
        master_channel_id: MasterChannelId,
        vc_id: int,
        ocf_flag: bool,
        master_ch_frame_count: int,
        vc_frame_count: int,
        frame_datafield_status: TransferFrameDataFieldStatus,
    ):
        self.master_channel_id = master_channel_id
        self.vc_id = vc_id
        self.ocf_flag = ocf_flag
        self.master_ch_frame_count = master_ch_frame_count
        self.vc_frame_count = vc_frame_count
        self.frame_datafield_status = frame_datafield_status

    def pack(self, data: TmFramePrimaryHeader) -> bytes:
        packed = bytearray(6)
        packed[0] = data.master_channel_id.transfer_frame_version << 6
        packed[0] = packed[0] | data.master_channel_id.spacecraft_id >> 4
        packed[1] = (data.master_channel_id.spacecraft_id & 0b1111) << 4
        packed[1] = packed[1] | data.vc_id << 1
        packed[1] = packed[1] | data.ocf_flag
        packed[2] = data.master_ch_frame_count
        packed[3] = data.vc_frame_count
        packed[4:6] = data.frame_datafield_status.pack(data.frame_datafield_status)
        return bytes(packed)

    @classmethod
    def unpack(cls, data: bytes) -> TmFramePrimaryHeader:
        tf_version = (data[0] >> 6) & 0b11
        spacecraft_id = (data[0] & 0b111111) << 4 | (data[1] >> 4) & 0b1111
        master_channel_id = MasterChannelId(tf_version, spacecraft_id)
        vc_id = (data[1] >> 1) & 0b111
        ocf_flag = bool(data[1] & 0b1)
        master_ch_frame_count = data[2]
        vc_frame_count = data[3]
        frame_datafield_status = TransferFrameDataFieldStatus.unpack(data[4:])
        return cls(
            master_channel_id,
            vc_id,
            ocf_flag,
            master_ch_frame_count,
            vc_frame_count,
            frame_datafield_status,
        )


@dataclass
class TransferFrameSecondaryHeader:
    version_number: int
    secondary_header_len: int
    data_field: bytes

    def pack(self, data: TransferFrameSecondaryHeader) -> bytes:
        packed = bytearray(1)
        packed[0] = data.version_number << 6
        packed[0] = packed[0] | data.secondary_header_len
        if data.secondary_header_len <= 63:
            packed.extend(data.data_field)
        else:
            raise ValueError(
                f"Secondary header length too long (max 63 octets): {data.secondary_header_len}"
            )
        return bytes(packed)

    @classmethod
    def unpack(cls, data: bytes) -> TransferFrameSecondaryHeader:
        if len(data) < 1:
            raise BytesTooShortError(1, len(data))
        secondary_header_len = data[0] & 0b111111
        return cls(
            version_number=(data[0] >> 6) & 0b11,
            secondary_header_len=secondary_header_len,
            data_field=data[1 : 1 + secondary_header_len],
        )


class TmTransferFrame:
    def __init__(
        self,
        length: int,
        primary_header: TmFramePrimaryHeader,
        secondary_header: Optional[TransferFrameSecondaryHeader],
        data_field: bytes,
        op_ctrl_field: Optional[bytes],
        frame_error_control: Optional[bytes],
    ) -> None:
        if length < 2048:  # According to CCSDS TM SYNCHRONIZATION AND CHANNEL CODING Blue Book
            self.length = length
        else:
            raise ValueError(f"Tm frame length {length} exceeds maximum of 2048.")
        self.primary_header = primary_header
        self.secondary_header = secondary_header
        self.data_field = data_field
        self.op_ctrl_field = op_ctrl_field
        self.frame_error_control = frame_error_control

    def pack(self, data: TmTransferFrame) -> bytes:
        packed = bytearray()
        packed.extend(data.primary_header.pack(data.primary_header))
        if data.primary_header.frame_datafield_status.secondary_header_flag:
            packed.extend(data.secondary_header.pack(data.secondary_header))
        packed.extend(data.data_field)
        if data.op_ctrl_field is not None:
            packed.extend(data.op_ctrl_field)
        if data.frame_error_control is not None:
            packed.extend(data.frame_error_control)
        if len(packed) != data.length:
            raise ValueError(
                f"Transfer frame length {len(packed)} not equal to expected length {data.length}"
            )
        return bytes(packed)

    @classmethod
    def unpack(
        cls, raw_frame: bytes, length: int, has_error_control_field: bool
    ) -> TmTransferFrame:
        primary_header = TmFramePrimaryHeader.unpack(raw_frame)
        secondary_header = None
        current_idx = 6
        if primary_header.frame_datafield_status.secondary_header_flag:
            secondary_header = TransferFrameSecondaryHeader.unpack(
                raw_frame[current_idx:]
            )
            current_idx += 1 + secondary_header.secondary_header_len
        data_end = len(raw_frame)
        op_ctrl_field = None
        frame_error_control = None
        if has_error_control_field:
            # check for too-short fefc
            if primary_header.ocf_flag:
                len_data = length - current_idx - 6
                if current_idx + len_data + 6 > len(raw_frame):
                    raise BytesTooShortError(current_idx + len_data + 6, len(raw_frame))
            else:
                len_data = length - current_idx - 2
                if current_idx + len_data + 2 > len(raw_frame):
                    raise BytesTooShortError(current_idx + len_data + 2, len(raw_frame))
            frame_error_control = raw_frame[-2:]
            # CRC16-CCITT checksum
            if CRC16_CCITT_FUNC(raw_frame) != 0:
                raise InvalidCrcCcitt16(raw_frame)
            # Used for length checks.
            data_end -= 2
        if primary_header.ocf_flag:
            if current_idx + 4 > len(raw_frame):
                raise BytesTooShortError(current_idx + 4, len(raw_frame))
            if has_error_control_field:
                op_ctrl_field = raw_frame[-6:-2]
            else:
                op_ctrl_field = raw_frame[-4:]
            data_end -= 4
        frame_data_field = raw_frame[current_idx:data_end]
        return cls(
            len(raw_frame),
            primary_header,
            secondary_header,
            frame_data_field,
            op_ctrl_field,
            frame_error_control,
        )
