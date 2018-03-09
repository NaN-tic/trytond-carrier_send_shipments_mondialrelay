# This file is part of the carrier_send_shipments_mondialrelay module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class CarrierSendShipmentsMondialRelayTestCase(ModuleTestCase):
    'Test Carrier Send Shipments MondialRelay module'
    module = 'carrier_send_shipments_mondialrelay'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        CarrierSendShipmentsMondialRelayTestCase))
    return suite