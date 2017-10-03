import unittest

from openprocurement.tender.core.tests.configurator import ConfiguratorTestMixin

from openprocurement.tender.competitivedialogue.adapters import (
    TenderCDEUConfigurator, TenderCDUAConfigurator)

from openprocurement.tender.competitivedialogue.models import (
    CompetitiveDialogEU, CompetitiveDialogUA)


class ConfiguratorTestTenderCDEUConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDEUConfigurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = CompetitiveDialogEU


class ConfiguratorTestTenderCDUAConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderCDUAConfigurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = CompetitiveDialogUA


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDEUConfigurator))
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderCDUAConfigurator))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
