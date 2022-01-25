import enum
import struct


USLP_VERSION_NUMBER = 0b1100


class SourceOrDestField(enum.IntEnum):
    SOURCE = 0
    DEST = 1


class BypassSequenceControlFlag(enum.IntEnum):
    SEQ_CTRLD_QOS = 0
    EXPEDITED_QOS = 1


class ProtocolCommandFlag(enum.IntEnum):
    USER_DATA = (0,)
    PROTOCOL_INFORMATION = 1


class UslpPrimaryHeaderBase:
    """Trucated USLP transfer frame primary header with a length of 4 bytes. For more information,
    refer to the USLP Blue Book CCSDS 732.1-B-2.
    p.163

    Only contains a subset of the regular primary header
    1. Transfer Frame Version Number or TFVN (4 bits)
    2. Spacecraft ID or SCID (16 bits)
    3. Source or destination identifier (1 bit)
    4. Virtual Channel ID or VCID (6 bits)
    5. Multiplexer Access Point or MAP ID (4 bits)
    6. End of Frame Primary Header (1 bit)
    """

    def __init__(
        self,
        scid: int,
        src_dest: SourceOrDestField,
        vcid: int,
        map_id: int,
    ):
        self.scid = scid
        self.src_dest = src_dest
        self.vcid = vcid
        self.map_id = map_id

    def pack(self) -> bytearray:
        return self.pack_truncated_header()

    def pack_truncated_header(self) -> bytearray:
        packet = bytearray()
        packet.append(USLP_VERSION_NUMBER | (self.scid >> 12) & 0b1111)
        packet.append((self.scid >> 4) & 0xFF)
        packet.append(
            ((self.scid & 0b1111) << 4)
            | (self.src_dest << 3)
            | (self.vcid >> 3) & 0b111
        )
        packet.append((self.vcid & 0b111) << 5 | self.map_id << 1)
        return packet


class UslpPrimaryHeader(UslpPrimaryHeaderBase):
    """USLP transfer frame primary header with a length of 4 to 14 bytes. It consists of 13
    fields positioned contiguously. For more information, refer to the USLP Blue Book
    CCSDS 732.1-B-2 p.77

    1. Transfer Frame Version Number or TFVN (4 bits)
    2. Spacecraft ID or SCID (16 bits)
    3. Source or destination identifier (1 bit)
    4. Virtual Channel ID or VCID (6 bits)
    5. Multiplexer Access Point or MAP ID (4 bits)
    6. End of Frame Primary Header (1 bit)
    7. Frame Length (16 bits)
    8. Bypass/Sequence Control Flag (1 bit)
    9. Protocol Control Command Flag (1 bit)
    10. Reserve Spares (2 bits)
    11. OCF flag (1 bit)
    12. VCF count length (3 bits)
    13. VCF count (0 to 56 bits)
    """

    def __init__(
        self,
        scid: int,
        src_dest: SourceOrDestField,
        vcid: int,
        map_id: int,
        frame_len: int,
        bypass_seq_ctrl_flag: BypassSequenceControlFlag,
        prot_ctrl_cmd_flag: ProtocolCommandFlag,
        op_ctrl_flag: bool,
        vcf_count_len: int,
        vcf_count: int,
    ):
        super().__init__(scid, src_dest, vcid, map_id)
        self.frame_len = frame_len
        self.bypass_seq_ctrl_flag = bypass_seq_ctrl_flag
        self.prot_ctrl_cmd_flag = prot_ctrl_cmd_flag
        self.op_ctrl_flag = op_ctrl_flag
        self.vcf_count_len = vcf_count_len
        self.vcf_count = vcf_count

    def pack(self) -> bytearray:
        packet = self.pack_truncated_header()
        packet.append((self.frame_len >> 8) & 0xFF)
        packet.append(self.frame_len & 0xFF)
        packet.append(
            (self.bypass_seq_ctrl_flag << 7)
            | (self.prot_ctrl_cmd_flag << 6)
            | (self.op_ctrl_flag << 3)
            | self.vcf_count_len
        )
        if self.vcf_count_len == 1:
            packet.append(self.vcf_count)
        elif self.vcf_count_len == 2:
            packet.extend(struct.pack("!H", self.vcf_count))
        elif self.vcf_count_len == 4:
            packet.extend(struct.pack("!I", self.vcf_count))
        else:
            for idx in range(self.vcf_count_len, 0, -1):
                packet.append(self.vcf_count_len >> (idx * 8 - 1) & 0xFF)
        return packet


TruncatedUslpPrimaryHeader = UslpPrimaryHeaderBase
