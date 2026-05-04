from unittest import TestCase

from spacepackets.ecss import pus_3_hk, pus_5_event, pus_17_test


class TestMessageSubtypeCompat(TestCase):
    def test_service_17_exports_legacy_subservice_enum_alias(self):
        self.assertIs(pus_17_test.Subservice, pus_17_test.MessageSubtype)

    def test_service_3_exports_legacy_subservice_enum_alias(self):
        self.assertIs(pus_3_hk.Subservice, pus_3_hk.MessageSubtype)

    def test_service_5_exports_legacy_subservice_enum_alias(self):
        self.assertIs(pus_5_event.Subservice, pus_5_event.MessageSubtype)
