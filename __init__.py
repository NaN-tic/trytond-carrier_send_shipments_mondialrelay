# This file is part of the carrier_send_shipments_mondialrelay module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# copyright notices and license terms. the full
from trytond.pool import Pool
from . import api
from . import address
from . import shipment


def register():
    Pool.register(
        address.Address,
        api.CarrierApi,
        shipment.ShipmentOut,
        module='carrier_send_shipments_mondialrelay', type_='model')
