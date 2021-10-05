# -*- coding: utf-8 -*-
"""Deserialize PUS Service 1 Verification TM
"""
from __future__ import annotations
import struct
from typing import Deque

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.tm import PusVersion, PusTelemetry

from spacepackets.log import get_console_logger


class Service1TM:
    """Service 1 TM class representation. Can be used to deserialize raw service 1 packets.
    """
    def __init__(
            self, subservice_id: int, time: CdsShortTimestamp = None,
            tc_packet_id: int = 0, tc_psc: int = 0, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, packet_version: int = 0b000,
            pus_version: PusVersion = PusVersion.GLOBAL_CONFIG, pus_tm_version: int = 0b0001,
            ack: int = 0b1111, secondary_header_flag: bool = True, space_time_ref: int = 0b0000,
            destination_id: int = 0
    ):
        self.pus_tm = PusTelemetry(
            service_id=1,
            subservice_id=subservice_id,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            pus_tm_version=pus_tm_version,
            ack=ack,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id
        )
        self.has_tc_error_code = False
        self.is_step_reply = False
        # Failure Reports with error code
        self.err_code = 0
        self.step_number = 0
        self.error_param1 = 0
        self.error_param2 = 0
        self.tc_packet_id = tc_packet_id
        self.tc_psc = tc_psc
        self.tc_ssc = tc_psc & 0x3fff

    @classmethod
    def __empty(cls) -> Service1TM:
        return cls(
            subservice_id=0
        )

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, pus_version: PusVersion = PusVersion.GLOBAL_CONFIG
    ) -> Service1TM:
        """Parse a service 1 telemetry packet

        :param raw_telemetry:
        :param pus_version:
        :raises ValueError: Raw telemetry too short
        :return:
        """
        service_1_tm = cls.__empty()
        service_1_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        tm_data = service_1_tm.pus_tm.get_tm_data()
        if len(tm_data) < 4:
            logger = get_console_logger()
            logger.warning("TM data less than 4 bytes!")
            raise ValueError
        service_1_tm.tc_packet_id = tm_data[0] << 8 | tm_data[1]
        service_1_tm.tc_psc = tm_data[2] << 8 | tm_data[3]
        service_1_tm.tc_ssc = service_1_tm.tc_psc & 0x3fff
        if service_1_tm.pus_tm.get_subservice() % 2 == 0:
            service_1_tm._handle_failure_verification()
        else:
            service_1_tm._handle_success_verification()
        return service_1_tm

    def _handle_failure_verification(self):
        """Handle parsing a verification failure packet, subservice ID 2, 4, 6 or 8
        """
        self.has_tc_error_code = True
        tm_data = self.pus_tm.get_tm_data()
        subservice = self.pus_tm.get_subservice()
        expected_len = 14
        if subservice == 6:
            self.is_step_reply = True
            expected_len = 15
        elif subservice not in [2, 4, 8]:
            logger = get_console_logger()
            logger.error("Service1TM: Invalid subservice")
        if len(tm_data) < expected_len:
            logger = get_console_logger()
            logger.warning(f'PUS TM[1,{subservice}] source data smaller than expected 15 bytes')
            raise ValueError
        current_idx = 4
        if self.is_step_reply:
            self.step_number = struct.unpack('>B', tm_data[current_idx: current_idx + 1])[0]
            current_idx += 1
        self.err_code = struct.unpack('>H', tm_data[current_idx: current_idx + 2])[0]
        current_idx += 2
        self.error_param1 = struct.unpack('>I', tm_data[current_idx: current_idx + 4])[0]
        current_idx += 2
        self.error_param2 = struct.unpack('>I', tm_data[current_idx: current_idx + 4])[0]

    def _handle_success_verification(self):
        if self.pus_tm.get_subservice() == 5:
            self.is_step_reply = True
            self.step_number = struct.unpack('>B', self.get_tm_data()[4:5])[0]
        elif self.pus_tm.get_subservice() not in [1, 3, 7]:
            logger = get_console_logger()
            logger.warning("Service1TM: Invalid subservice")

    def get_tc_ssc(self):
        return self.tc_ssc

    def get_error_code(self):
        if self.has_tc_error_code:
            return self.err_code
        else:
            logger = get_console_logger()
            logger.warning("Service1TM: get_error_code: This is not a failure packet, returning 0")
            return 0

    def get_step_number(self):
        if self.is_step_reply:
            return self.step_number
        else:
            logger = get_console_logger()
            logger.warning("Service1TM: get_step_number: This is not a step reply, returning 0")
            return 0
