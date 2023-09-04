from typing import Deque
from spacepackets.cfdp.conf import ByteFieldU8
from spacepackets.cfdp.defs import ChecksumType, TransmissionMode
from spacepackets.cfdp.pdu import (
    MetadataParams,
    MetadataPdu,
    FileDataPdu,
    EofPdu,
    PduConfig,
)
from spacepackets.cfdp.pdu.file_data import FileDataParams
from crcmod.predefined import PredefinedCrc

LOCAL_ID = ByteFieldU8(1)
REMOTE_ID = ByteFieldU8(2)

file_transfer_queue = Deque()
src_name = "/tmp/src-file.txt"
dest_name = "/tmp/dest-file.txt"
file_data = "Hello World!"
seq_num = ByteFieldU8(0)
pdu_conf = PduConfig(LOCAL_ID, REMOTE_ID, seq_num, TransmissionMode.UNACKNOWLEDGED)
metadata_params = MetadataParams(
    True, ChecksumType.CRC_32, len(file_data), src_name, dest_name
)
metadata_pdu = MetadataPdu(pdu_conf, metadata_params)

file_transfer_queue.append(metadata_pdu)

params = FileDataParams(file_data.encode(), 0)
fd_pdu = FileDataPdu(pdu_conf, params)

file_transfer_queue.append(fd_pdu)

crc_calculator = PredefinedCrc("crc32")
crc_calculator.update(file_data.encode())
crc_32 = crc_calculator.digest()
eof_pdu = EofPdu(pdu_conf, crc_32, len(file_data))
file_transfer_queue.append(eof_pdu)

for idx, pdu in enumerate(file_transfer_queue):
    print(f"PDU {idx}: {pdu}")
