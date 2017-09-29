import unittest

from openprocurement.api.tests.base import snitch
from openprocurement.tender.core.tests.configurator import ConfiguratorTestMixin

from openprocurement.tender.competitivedialogue.adapters import (
    TenderCDEUConfigurator, TenderCDUAConfigurator,
    TenderCDEUStage2Configurator, TenderCDUAStage2Configurator)



class ConfiguratorTestTenderCDEUStage2Configurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDEUStage2Configurator


class ConfiguratorTestTenderCDEUConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDEUConfigurator


class ConfiguratorTestTenderCDUAConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDUAConfigurator


class ConfiguratorTestTenderCDUAStage2Configurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDUAStage2Configurator


def suite():
    current_suite = unittest.TestSuite()
    current_suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDEUStage2Configurator))
    current_suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDEUConfigurator))
    current_suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDUAConfigurator))
    current_suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDUAStage2Configurator))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
