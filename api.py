# This file is part of the carrier_send_shipments_mondialrelay module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Not, Equal
from mondialrelay.picking import *
from mondialrelay.utils import (MRELAY_VERSION, MRELAY_CULTURE,
    MRELAY_LABEL_FORMAT, MRELAY_PDF_FORMAT)
import logging

MRVERSION = [(o, o) for o in MRELAY_VERSION]
MRCULTURE = [(o, o) for o in MRELAY_CULTURE]
MRLABEL_FORMAT = [(o, o) for o in MRELAY_LABEL_FORMAT]
MRPDF_FORMAT = [(o, o) for o in MRELAY_PDF_FORMAT]

__all__ = ['CarrierApi']


class CarrierApi:
    __metaclass__ = PoolMeta
    __name__ = 'carrier.api'
    mondialrelay_version = fields.Selection(MRVERSION,
        'Mondial Relay Version', states={
            'required': Eval('method') == 'mondialrelay',
        }, depends=['method'])
    mondialrelay_customerid = fields.Char('Mondial Relay Customer ID',
        states={
            'required': Eval('method') == 'mondialrelay',
        }, depends=['method'])
    mondialrelay_culture = fields.Selection(MRCULTURE,
        'Mondial Relay Culture', states={
            'required': Eval('method') == 'mondialrelay',
        }, depends=['method'])
    mondialrelay_label = fields.Selection(MRLABEL_FORMAT,
        'Mondial Relay Label Format', states={
            'required': Eval('method') == 'mondialrelay',
        }, depends=['method'])
    mondialrelay_pdf_format = fields.Selection(MRPDF_FORMAT,
        'Mondial Relay PDF')
    mondialrelay_content = fields.Char('MondialRelay Content',
        help='Description package content (livres, ...)')

    @classmethod
    def get_carrier_app(cls):
        'Add Carrier MondialRelay APP'
        res = super(CarrierApi, cls).get_carrier_app()
        res.append(('mondialrelay', 'MondialRelay'))
        return res

    @classmethod
    def view_attributes(cls):
        return super(CarrierApi, cls).view_attributes() + [
            ('//page[@id="mondialrelay"]', 'states', {
                    'invisible': Not(Equal(Eval('method'), 'mondialrelay')),
                    })]

    @classmethod
    def test_mondialrelay(cls, api):
        'Test MondialRelay connection'
        message = 'MondialRelay test is not available'
        cls.raise_user_error(message)
