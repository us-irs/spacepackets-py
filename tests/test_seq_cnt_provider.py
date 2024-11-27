import os
import platform
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase

from spacepackets.seqcount import CcsdsFileSeqCountProvider


class TestSeqCount(TestCase):
    def setUp(self) -> None:
        self.file_name = Path("seq_cnt.txt")

    def test_basic(self):
        if platform.system() != "Windows":
            with NamedTemporaryFile("w+t") as file:
                file.write("0\n")
                file.seek(0)
                seq_cnt_provider = CcsdsFileSeqCountProvider(Path(file.name))
                seq_cnt = seq_cnt_provider.current()
                self.assertEqual(seq_cnt, 0)
                # The first call will start at 0
                self.assertEqual(next(seq_cnt_provider), 0)
                self.assertEqual(seq_cnt_provider.get_and_increment(), 1)
                file.seek(0)
                file.write(f"{pow(2, 14) - 1}\n")
                file.flush()
                # Assert rollover
                self.assertEqual(next(seq_cnt_provider), pow(2, 14) - 1)
                self.assertEqual(next(seq_cnt_provider), 0)

    def test_with_real_file(self):
        seq_cnt_provider = CcsdsFileSeqCountProvider(self.file_name)
        self.assertTrue(self.file_name.exists())
        self.assertEqual(seq_cnt_provider.current(), 0)
        self.assertEqual(next(seq_cnt_provider), 0)

    def test_file_deleted_runtime(self):
        seq_cnt_provider = CcsdsFileSeqCountProvider(self.file_name)
        self.assertTrue(self.file_name.exists())
        os.remove(self.file_name)
        with self.assertRaises(FileNotFoundError):
            next(seq_cnt_provider)
        with self.assertRaises(FileNotFoundError):
            seq_cnt_provider.current()

    def test_faulty_file_entry(self):
        if platform.system() != "Windows":
            with NamedTemporaryFile("w+t") as file:
                file.write("-1\n")
                file.seek(0)
                seq_cnt_provider = CcsdsFileSeqCountProvider(Path(file.name))
                with self.assertRaises(ValueError):
                    next(seq_cnt_provider)
                file.write(f"{pow(2, 15)}\n")
                file.seek(0)
                file.flush()
                seq_cnt_provider = CcsdsFileSeqCountProvider(Path(file.name))
                with self.assertRaises(ValueError):
                    next(seq_cnt_provider)

    def tearDown(self) -> None:
        if self.file_name.exists():
            os.remove(self.file_name)
