import unittest
from openprocurement.tender.competitivedialogue.adapters import (
    TenderCDEUConfigurator, TenderCDUAConfigurator,
    TenderCDEUStage2Configurator,TenderCDUAStage2Configurator)


class ConfiguratorValueTest(unittest.TestCase):
    def test_reverse_awarding_criteria(self):
        self.assertEqual(TenderCDEUConfigurator.reverse_awarding_criteria, False)
        self.assertEqual(TenderCDUAConfigurator.reverse_awarding_criteria, False)
        self.assertEqual(TenderCDEUStage2Configurator.reverse_awarding_criteria, False)
        self.assertEqual(TenderCDUAStage2Configurator.reverse_awarding_criteria, False)

    def test_awarding_criteria_key(self):
        self.assertEqual(TenderCDEUConfigurator.awarding_criteria_key, 'amountPerfomance')
        self.assertEqual(TenderCDUAConfigurator.awarding_criteria_key, 'amountPerfomance')
        self.assertEqual(TenderCDEUStage2Configurator.awarding_criteria_key, 'amountPerfomance')
        self.assertEqual(TenderCDUAStage2Configurator.awarding_criteria_key, 'amountPerfomance')


def suite():
    current_suite = unittest.TestSuite()
    current_suite.addTest(unittest.makeSuite(ConfiguratorValueTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
