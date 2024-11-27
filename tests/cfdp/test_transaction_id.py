from unittest import TestCase

from spacepackets.cfdp import TransactionId
from spacepackets.util import ByteFieldU16


class TestTransactionId(TestCase):
    def setUp(self):
        self.transaction_id_0 = TransactionId(ByteFieldU16(5), ByteFieldU16(6))
        self.transaction_id_1 = TransactionId(ByteFieldU16(5), ByteFieldU16(7))

    def test_hashable(self):
        # Simply test whether the ID can be used as a dictionary key.
        test_dict = {self.transaction_id_0: "test 1"}
        test_dict.update({self.transaction_id_1: "test 2"})
        self.assertEqual(len(test_dict), 2)

    def test_eq(self):
        self.assertNotEqual(self.transaction_id_0, self.transaction_id_1)

    def test_repr(self):
        repr_str = self.transaction_id_0.__repr__()
        self.assertTrue("TransactionId" in repr_str)
        self.assertTrue("source_entity_id=" in repr_str)
        self.assertTrue("transaction_seq_num=" in repr_str)
