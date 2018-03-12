# This file is part of the carrier_send_shipments_mondialrelay module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.transaction import Transaction
from mondialrelay.picking import Picking
from trytond.modules.carrier_send_shipments.tools import unaccent
from base64 import decodestring
import logging
import tempfile

__all__ = ['ShipmentOut']
logger = logging.getLogger(__name__)


class ShipmentOut:
    __metaclass__ = PoolMeta
    __name__ = 'stock.shipment.out'
    mondialrelay_content = fields.Char('MondialRelay Content',
        help='Description package content (livres, ...)')

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        cls._error_messages.update({
            'mondialrelay_add_services': ('Select a service or default '
                'service in MondialRelay API'),
            'mondialrelay_address': ('Delivery address "%(name)s" has not '
                'a country or MondialRelay location.'),
            'mondialrelay_not_send_error': ('Not send shipment %(name)s. '
                '%(error)s'),
            'mondialrelay_not_label': ('Not available "%(name)s" label '
                'from MondialRelay'),
            })

    @staticmethod
    def mondialrelay_picking_data(api, shipment, service, price, weight=False):
        '''
        MondialRelay Picking Data
        :param api: obj
        :param shipment: obj
        :param service: str
        :param price: decimal
        :param weight: bol
        Return data
        '''
        Uom = Pool().get('product.uom')

        packages = shipment.number_packages
        if not packages or packages == 0:
            packages = 1

        delivery_address = shipment.delivery_address
        remitente_address = (shipment.warehouse.address
            or shipment.company.party.addresses[0])

        if api.reference_origin and hasattr(shipment, 'origin'):
            code = shipment.origin and shipment.origin.rec_name or shipment.code
        else:
            code = shipment.code

        def _phonenumber(country, value):
            # TODO use phonenumber package
            return '+%s%s' % (country.phonenumber,
                unaccent(value).replace(' ', ''))

        data = {}
        data['OrderNo'] = code
        # data['ParcelCount'] = '1'
        data['DeliveryMode'] = service.code
        data['DeliveryLocation'] = delivery_address.mondialrelay
        # data['CollectionMode'] =
        # data['CollectionLocation'] =
        data['ParcelContent'] = (shipment.mondialrelay_content
            or api.mondialrelay_content or '')
        data['DeliveryInstruction'] = (unaccent(shipment.carrier_notes)
            if shipment.carrier_notes else '')
        # data['SenderTitle'] =
        data['SenderFirstname'] = shipment.company.party.name
        # data['SenderLastname'] =
        data['SenderStreetname'] = unaccent(remitente_address.street)
        # data['SenderHouseNo'] =
        data['SenderCountryCode'] = (remitente_address.country
            and remitente_address.country.code or '')
        data['SenderPostCode'] = remitente_address.zip
        data['SenderCity'] = unaccent(remitente_address.city)
        # data['SenderAddressAdd1'] =
        # data['SenderAddressAdd2'] =
        # data['SenderAddressAdd3'] =

        rphone = (remitente_address.phone
            or shipment.company.party.get_mechanism('phone'))
        if rphone:
            data['SenderPhoneNo'] = _phonenumber(
                remitente_address.country, rphone)
        rmobile = (remitente_address.mobile
            or shipment.company.party.get_mechanism('mobile'))
        if rmobile:
            data['SenderMobileNo'] = _phonenumber(
                remitente_address.country, rmobile)
        data['SenderEmail'] = (remitente_address.email
            or shipment.company.party.get_mechanism('email'))

        # data['RecipientTitle'] =
        data['RecipientFirstname'] = unaccent(shipment.customer.name)
        # data['RecipientLastname'] =
        data['RecipientStreetname'] = unaccent(delivery_address.street)
        # data['RecipientHouseNo'] =
        data['RecipientCountryCode'] = delivery_address.country.code
        data['RecipientPostCode'] = delivery_address.zip
        data['RecipientCity'] = unaccent(delivery_address.city)
        # data['RecipientAddressAdd1'] =
        # data['RecipientAddressAdd2'] =
        # data['RecipientAddressAdd3'] =

        dphone = (delivery_address.phone
            or shipment.customer.get_mechanism('phone'))
        if dphone:
            data['SenderPhoneNo'] = _phonenumber(
                remitente_address.country, dphone)
        dmobile = (delivery_address.phone
            or shipment.customer.get_mechanism('mobile'))
        if dmobile:
            data['SenderMobileNo'] = _phonenumber(
                remitente_address.country, dmobile)
        data['RecipientEmail'] = (delivery_address.email
            or shipment.customer.get_mechanism('email'))

        if weight and hasattr(shipment, 'weight_func'):
            weight = shipment.weight_func
            unit = 'gr'
            if weight == 0:
                weight = 1
            if api.weight_api_unit:
                if shipment.weight_uom:
                    sunit = shipment.weight_uom
                    weight = Uom.compute_qty(sunit, weight, api.weight_api_unit)
                    unit = 'gr' if sunit.symbol == 'g' else sunit.symbol
                elif api.weight_unit:
                    wunit = api.weight_unit
                    weight = Uom.compute_qty(wunit, weight, api.weight_api_unit)
                    unit = 'gr' if wunit.symbol == 'g' else wunit.symbol
            data['Weight'] = weight
            data['WeightUnit'] = unit

        return data

    @classmethod
    def send_mondialrelay(self, api, shipments):
        '''
        Send shipments out to mondialrelay
        :param api: obj
        :param shipments: list
        Return references, labels, errors
        '''
        pool = Pool()
        CarrierApi = pool.get('carrier.api')
        ShipmentOut = pool.get('stock.shipment.out')

        references = []
        labels = []
        errors = []

        default_service = CarrierApi.get_default_carrier_service(api)
        dbname = Transaction().cursor.dbname

        with Picking(api.username, api.password, api.mondialrelay_customerid,
                api.mondialrelay_culture, api.mondialrelay_label,
                api.mondialrelay_pdf_format, api.mondialrelay_version,
                timeout=api.timeout, debug=api.debug) as picking_api:
            for shipment in shipments:
                service = (shipment.carrier_service or shipment.carrier.service
                    or default_service)
                if not service:
                    message = self.raise_user_error('mondialrelay_add_services', {},
                        raise_exception=False)
                    errors.append(message)
                    continue

                if (not shipment.delivery_address.country
                        or not shipment.delivery_address.mondialrelay):
                    message = self.raise_user_error('mondialrelay_address', {
                        'name': shipment.delivery_address.rec_name,
                        }, raise_exception=False)
                    errors.append(message)
                    continue

                if shipment.carrier_cashondelivery:
                    price = shipment.carrier_cashondelivery_price
                else:
                    price = shipment.total_amount_func

                data = self.mondialrelay_picking_data(
                    api, shipment, service, price, api.weight)
                reference, label, error = picking_api.create(data)

                if reference:
                    self.write([shipment], {
                        'carrier_tracking_ref': reference,
                        'carrier_service': service,
                        'carrier_delivery': True,
                        'carrier_printed': True,
                        'carrier_send_date': ShipmentOut.get_carrier_date(),
                        'carrier_send_employee': ShipmentOut.get_carrier_employee() or None,
                        })
                    logger.info('Send shipment %s' % (shipment.code))
                    references.append(shipment.code)
                else:
                    logger.error('Not send shipment %s.' % (shipment.code))

                if label:
                    if api.mondialrelay_label == 'ZplCode':
                        ext = 'zpl'
                    elif api.mondialrelay_label == 'IplCode':
                        ext = 'ipl'
                    else:
                        ext = 'pdf'
                    with tempfile.NamedTemporaryFile(
                            prefix='%s-mondialrelay-%s-' % (dbname, reference),
                            suffix='.%s' % ext, delete=False) as temp:
                        temp.write(label)
                    logger.info('Generated tmp label %s' % (temp.name))
                    temp.close()
                    labels.append(temp.name)
                else:
                    message = self.raise_user_error('mondialrelay_not_label', {
                            'name': shipment.rec_name,
                            }, raise_exception=False)
                    errors.append(message)
                    logger.error(message)

                if error:
                    message = self.raise_user_error('mondialrelay_not_send_error', {
                            'name': shipment.rec_name,
                            'error': error,
                            }, raise_exception=False)
                    logger.error(message)
                    errors.append(message)

        return references, labels, errors

    @classmethod
    def print_labels_mondialrelay(self, api, shipments):
        '''
        Get MondialRelay labels from Shipment Out
        Not available labels from MondialRelay API. Not return labels
        '''
        labels = []
        return labels
