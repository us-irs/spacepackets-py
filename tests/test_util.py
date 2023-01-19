import struct
from unittest import TestCase

from spacepackets.util import (
    ByteFieldGenerator,
    ByteFieldU8,
    ByteFieldU16,
    ByteFieldU32,
    UnsignedByteField,
    IntByteConversion,
)


class TestUtility(TestCase):
    def test_basic_bytefields(self):
        byte_field = ByteFieldU8(22)
        self.assertEqual(int(byte_field), 22)
        byte_field = ByteFieldU16(5292)
        self.assertEqual(int(byte_field), 5292)
        byte_field = ByteFieldU32(129302)
        self.assertEqual(struct.unpack("!I", byte_field.as_bytes)[0], 129302)
        with self.assertRaises(ValueError):
            ByteFieldU8(900)

    def test_one_byte_field_gen(self):
        one_byte_test = ByteFieldGenerator.from_int(byte_len=1, val=0x42)
        self.assertEqual(ByteFieldU8(0x42), one_byte_test)
        one_byte_test = ByteFieldGenerator.from_bytes(1, one_byte_test.as_bytes)
        self.assertEqual(ByteFieldU8(0x42), one_byte_test)

    def test_one_byte_invalid_gen(self):
        with self.assertRaises(ValueError) as cm:
            ByteFieldGenerator.from_int(byte_len=1, val=0x4217)
        self.assertEqual(
            str(cm.exception),
            f"Passed value {0x4217} larger than allowed 255 or negative",
        )
        with self.assertRaises(ValueError) as cm:
            ByteFieldGenerator.from_int(byte_len=1, val=-1)
        self.assertEqual(
            str(cm.exception), "Passed value -1 larger than allowed 255 or negative"
        )

    def test_byte_field_u8_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU8.from_bytes(bytes())

    def test_byte_field_u16_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU16.from_bytes(bytes([1]))

    def test_byte_field_u32_invalid_unpack(self):
        with self.assertRaises(ValueError):
            ByteFieldU32.from_bytes(bytes([1, 2, 3]))

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

    def test_setting_from_raw(self):
        one_byte_test = ByteFieldGenerator.from_int(byte_len=1, val=0x42)
        one_byte_test.value = bytes([0x22])
        self.assertEqual(int(one_byte_test), 0x22)
        self.assertEqual(one_byte_test.as_bytes, bytes([0x22]))
        with self.assertRaises(ValueError):
            one_byte_test.value = bytes()

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
