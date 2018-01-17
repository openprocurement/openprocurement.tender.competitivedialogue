import unittest

from openprocurement.tender.core.tests.configurator import ConfiguratorTestMixin

from openprocurement.tender.competitivedialogue.adapters import (
    TenderCDEUStage2Configurator, TenderCDUAStage2Configurator)

from openprocurement.tender.competitivedialogue.models import (
    TenderStage2EU, TenderStage2UA)


class ConfiguratorTestTenderCDEUStage2Configurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDEUStage2Configurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = TenderStage2EU


class ConfiguratorTestTenderCDUAStage2Configurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDUAStage2Configurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = TenderStage2UA


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDEUStage2Configurator))
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDUAStage2Configurator))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
