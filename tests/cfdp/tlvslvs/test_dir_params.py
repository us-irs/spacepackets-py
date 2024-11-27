from pathlib import Path
from unittest import TestCase

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import DirectoryParams


class TestDirParamsClass(TestCase):
    def setUp(self):
        self.dir_path = "/tmp"
        self.dir_path_from_str = CfdpLv.from_str(self.dir_path)
        self.dir_file_name = "~/dir-listing.txt"
        self.dir_file_name_from_str = CfdpLv.from_str(self.dir_file_name)
        self.dir_param = DirectoryParams(self.dir_path_from_str, self.dir_file_name_from_str)
        self.dir_param_from_strs = DirectoryParams.from_strs(self.dir_path, self.dir_file_name)
        # As POSIX to ensure this works on Windows as well.
        self.dir_param_from_paths = DirectoryParams.from_paths(
            Path(self.dir_path).as_posix(), Path(self.dir_file_name).as_posix()
        )

    def test_apis(self):
        self.assertEqual(self.dir_param, self.dir_param_from_strs)
        self.assertEqual(self.dir_param, self.dir_param_from_paths)
        self.assertEqual(self.dir_param_from_strs, self.dir_param_from_paths)
