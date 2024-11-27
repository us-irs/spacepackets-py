import struct
from unittest import TestCase

from spacepackets.util import (
    ByteFieldGenerator,
    ByteFieldU8,
    ByteFieldU16,
    ByteFieldU32,
    ByteFieldU64,
    IntByteConversion,
    UnsignedByteField,
)


class TestUtility(TestCase):
    def test_basic_bytefields(self):
        byte_field = ByteFieldU8(22)
        self.assertEqual(int(byte_field), 22)
        self.assertEqual(len(byte_field), 1)
        byte_field = ByteFieldU16(5292)
        self.assertEqual(int(byte_field), 5292)
        self.assertEqual(len(byte_field), 2)
        byte_field = ByteFieldU32(129302)
        self.assertEqual(struct.unpack("!I", byte_field.as_bytes)[0], 129302)
        self.assertEqual(len(byte_field), 4)
        with self.assertRaises(ValueError):
            ByteFieldU8(900)

    def test_one_byte_field_gen(self):
        one_byte_test = ByteFieldGenerator.from_int(byte_len=1, val=0x42)
        self.assertEqual(ByteFieldU8(0x42), one_byte_test)
        one_byte_test = ByteFieldGenerator.from_bytes(1, one_byte_test.as_bytes)
        self.assertEqual(ByteFieldU8(0x42), one_byte_test)

    def test_raw_to_object_one_byte(self):
        raw_bytefield = bytes([0x42])
        byte_field = UnsignedByteField.from_bytes(raw_bytefield)
        self.assertEqual(byte_field.value, 0x42)
        self.assertEqual(byte_field.byte_len, 1)

    def test_raw_to_object_two_bytes(self):
        raw_bytefield = bytes([0x07, 0xFF])
        byte_field = UnsignedByteField.from_bytes(raw_bytefield)
        self.assertEqual(byte_field.value, 0x07FF)
        self.assertEqual(byte_field.byte_len, 2)

    def test_raw_to_object_four(self):
        raw_bytefield = bytes([0x01, 0x02, 0x03, 0x04])
        byte_field = UnsignedByteField.from_bytes(raw_bytefield)
        self.assertEqual(byte_field.value, 0x01020304)
        self.assertEqual(byte_field.byte_len, 4)

    def test_raw_to_object_eight(self):
        raw_bytefield = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
        byte_field = UnsignedByteField.from_bytes(raw_bytefield)
        self.assertEqual(byte_field.value, 0x0102030405060708)
        self.assertEqual(byte_field.byte_len, 8)

    def test_one_byte_invalid_gen(self):
        with self.assertRaises(ValueError) as cm:
            ByteFieldGenerator.from_int(byte_len=1, val=0x4217)
        self.assertEqual(
            str(cm.exception),
            f"Passed value {0x4217} larger than allowed 255 or negative",
        )
        with self.assertRaises(ValueError) as cm:
            ByteFieldGenerator.from_int(byte_len=1, val=-1)
        self.assertEqual(str(cm.exception), "Passed value -1 larger than allowed 255 or negative")

    def test_byte_field_u8_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU8.from_u8_bytes(b"")

    def test_byte_field_u16_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU16.from_u16_bytes(bytes([1]))

    def test_byte_field_u32_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU32.from_u32_bytes(bytes([1, 2, 3]))

    def test_byte_field_u64_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU64.from_u64_bytes(bytes([1, 2, 3, 4, 5]))

    def test_byte_field_generator_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldGenerator.from_bytes(3, bytes([1, 2, 3, 4]))

    def test_byte_field_generator_invalid_unpack_2(self):
        with self.assertRaises(ValueError):
            ByteFieldGenerator.from_int(3, 25)

    def test_two_byte_field_gen(self):
        two_byte_test = ByteFieldGenerator.from_int(byte_len=2, val=0x1842)
        self.assertEqual(ByteFieldU16(0x1842), two_byte_test)
        two_byte_test = ByteFieldGenerator.from_bytes(2, two_byte_test.as_bytes)
        self.assertEqual(ByteFieldU16(0x1842), two_byte_test)

    def test_four_byte_field_gen(self):
        four_byte_test = ByteFieldGenerator.from_int(byte_len=4, val=0x10101010)
        self.assertEqual(ByteFieldU32(0x10101010), four_byte_test)
        four_byte_test = ByteFieldGenerator.from_bytes(4, four_byte_test.as_bytes)
        self.assertEqual(ByteFieldU32(0x10101010), four_byte_test)

    def test_eight_byte_field_gen(self):
        eight_byte_test = ByteFieldGenerator.from_int(byte_len=8, val=0x1010101010)
        self.assertEqual(ByteFieldU64(0x1010101010), eight_byte_test)
        eight_byte_test = ByteFieldGenerator.from_bytes(8, eight_byte_test.as_bytes)
        self.assertEqual(ByteFieldU64(0x1010101010), eight_byte_test)

    def test_setting_from_raw(self):
        one_byte_test = ByteFieldGenerator.from_int(byte_len=1, val=0x42)
        one_byte_test.value = bytes([0x22])
        self.assertEqual(int(one_byte_test), 0x22)
        self.assertEqual(one_byte_test.as_bytes, bytes([0x22]))
        with self.assertRaises(ValueError):
            one_byte_test.value = b""

    def invalid_byte_field_len(self):
        with self.assertRaises(ValueError):
            UnsignedByteField(0x42, 3)

    def test_byte_int_converter_signed_one_byte(self):
        minus_two_raw = IntByteConversion.to_signed(byte_num=1, val=-2)
        self.assertEqual(struct.unpack("!b", minus_two_raw)[0], -2)

    def test_byte_int_converter_signed_two_byte(self):
        raw = IntByteConversion.to_signed(byte_num=2, val=-32084)
        self.assertEqual(struct.unpack("!h", raw)[0], -32084)

    def test_byte_int_converter_signed_four_byte(self):
        raw = IntByteConversion.to_signed(byte_num=4, val=-7329093)
        self.assertEqual(struct.unpack("!i", raw)[0], -7329093)

    def test_byte_int_converter_signed_eight_byte(self):
        raw = IntByteConversion.to_signed(byte_num=8, val=-7329093032932932)
        self.assertEqual(struct.unpack("!q", raw)[0], -7329093032932932)

    def test_one_byte_str(self):
        byte_field = ByteFieldU8(22)
        self.assertEqual(
            str(byte_field),
            f"U8({byte_field.value}, 0x[{byte_field.as_bytes.hex(sep=',')}])",
        )

    def test_two_byte_str(self):
        byte_field = ByteFieldU16(8555)
        self.assertEqual(
            str(byte_field),
            f"U16({byte_field.value}, 0x[{byte_field.as_bytes.hex(sep=',')}])",
        )

    def test_four_byte_str(self):
        byte_field = ByteFieldU32(85323255)
        self.assertEqual(
            str(byte_field),
            f"U32({byte_field.value}, 0x[{byte_field.as_bytes.hex(sep=',')}])",
        )

    def test_one_byte_hex_str(self):
        byte_field = ByteFieldU8(22)
        self.assertEqual(byte_field.hex_str, f"{byte_field.value:#04x}")

    def test_two_byte_hex_str(self):
        byte_field = ByteFieldU16(2555)
        self.assertEqual(byte_field.hex_str, f"{byte_field.value:#06x}")

    def test_four_byte_hex_str(self):
        byte_field = ByteFieldU32(255532)
        self.assertEqual(byte_field.hex_str, f"{byte_field.value:#010x}")

    def test_eight_byte_hex_str(self):
        byte_field = ByteFieldU64(0x1010101010)
        self.assertEqual(byte_field.hex_str, f"{byte_field.value:#018x}")
