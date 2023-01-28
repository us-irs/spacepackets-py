import enum
import struct
from unittest import TestCase

from spacepackets.ecss import PacketFieldEnum
from spacepackets.ecss.fields import PacketFieldU8, PacketFieldU16, PacketFieldU32
from spacepackets.util import IntByteConversion


class ExampleEnum(enum.IntEnum):
    OH_NO = 0
    OH_YES = 1
    HMM = 2


class TestEcss(TestCase):
    def test_basic(self):
        self._enum_serialize_deserialize_different_sizes(8)
        self._enum_serialize_deserialize_different_sizes(16)
        self._enum_serialize_deserialize_different_sizes(32)
        self._enum_serialize_deserialize_different_sizes(64)
        with self.assertRaises(ValueError):
            IntByteConversion.unsigned_struct_specifier(12)
        with self.assertRaises(ValueError):
            IntByteConversion.unsigned_struct_specifier(0)
        with self.assertRaises(ValueError):
            IntByteConversion.signed_struct_specifier(12)
        with self.assertRaises(ValueError):
            IntByteConversion.signed_struct_specifier(0)

    def _enum_serialize_deserialize_different_sizes(self, pfc: int):
        for val in ExampleEnum:
            test_enum = PacketFieldEnum(pfc=pfc, val=val)
            self.assertEqual(test_enum.val, val)
            self.assertEqual(test_enum.pfc, pfc)
            raw_enum = test_enum.pack()
            fmt = ""
            if pfc == 8:
                fmt = "!B"
            elif pfc == 16:
                fmt = "!H"
            elif pfc == 32:
                fmt = "!I"
            elif pfc == 64:
                fmt = "!Q"
            self.assertEqual(raw_enum, bytearray(struct.pack(fmt, val)))
            test_enum_unpacked = PacketFieldEnum.unpack(pfc=pfc, data=raw_enum)
            self.assertEqual(test_enum_unpacked.val, val)
            self.assertEqual(test_enum_unpacked.pfc, pfc)

    def test_packet_field_helpers_u8(self):
        field_u8 = PacketFieldU8(10)
        self.assertEqual(field_u8.val, 10)
        self.assertEqual(field_u8.len(), 1)
        packed = field_u8.pack()
        self.assertEqual(packed, bytearray([10]))

    def test_packet_field_helpers_u16(self):
        field_u16 = PacketFieldU16(pow(2, 16) - 1)
        self.assertEqual(field_u16.val, pow(2, 16) - 1)
        self.assertEqual(field_u16.len(), 2)
        packed = field_u16.pack()
        self.assertEqual(packed, struct.pack("!H", pow(2, 16) - 1))

    def test_packet_field_helpers_u32(self):
        field_u16 = PacketFieldU32(pow(2, 32) - 1)
        self.assertEqual(field_u16.val, pow(2, 32) - 1)
        self.assertEqual(field_u16.len(), 4)
        packed = field_u16.pack()
        self.assertEqual(packed, struct.pack("!I", pow(2, 32) - 1))
