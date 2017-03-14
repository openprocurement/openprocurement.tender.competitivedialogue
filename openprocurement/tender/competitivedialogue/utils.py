# -*- coding: utf-8 -*-
from barbecue import vnmax
from logging import getLogger
from schematics.exceptions import ValidationError
from openprocurement.api.utils import (
    context_unpack, generate_id, get_now,
    set_ownership as api_set_ownership
)
from openprocurement.tender.core.utils import (
    save_tender, apply_patch, calculate_business_date
)
from openprocurement.tender.openua.constants import TENDERING_EXTRA_PERIOD
from openprocurement.tender.openua.utils import (
    check_complaint_status, has_unanswered_questions,
    has_unanswered_complaints
)
from openprocurement.tender.openeu.utils import (
    all_bids_are_reviewed, prepare_qualifications
)
from openprocurement.tender.openeu.constants import (
    PREQUALIFICATION_COMPLAINT_STAND_STILL as COMPLAINT_STAND_STILL
)
from openprocurement.tender.competitivedialogue.constants import (
    MINIMAL_NUMBER_OF_BIDS
)

LOGGER = getLogger(__name__)


def patch_eu(self):
    """Tender Edit (partial)

            For example here is how procuring entity can change number of items to be procured and total Value of a tender:

            .. sourcecode:: http

                PATCH /tenders/4879d3f8ee2443169b5fbbc9f89fa607 HTTP/1.1
                Host: example.com
                Accept: application/json

                {
                    "data": {
                        "value": {
                            "amount": 600
                        },
                        "itemsToBeProcured": [
                            {
                                "quantity": 6
                            }
                        ]
                    }
                }

            And here is the response to be expected:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Type: application/json

                {
                    "data": {
                        "id": "4879d3f8ee2443169b5fbbc9f89fa607",
                        "tenderID": "UA-64e93250be76435397e8c992ed4214d1",
                        "dateModified": "2014-10-27T08:12:34.956Z",
                        "value": {
                            "amount": 600
                        },
                        "itemsToBeProcured": [
                            {
                                "quantity": 6
                            }
                        ]
                    }
                }

            """
    tender = self.context
    if self.request.authenticated_role != 'Administrator' and tender.status in ['complete', 'unsuccessful',
                                                                                'cancelled']:
        self.request.errors.add('body', 'data', 'Can\'t update tender in current ({}) status'.format(tender.status))
        self.request.errors.status = 403
        return
    data = self.request.validated['data']
    if self.request.authenticated_role == 'tender_owner' and 'status' in data and \
            data['status'] not in ['active.pre-qualification.stand-still', 'active.stage2.waiting', tender.status]:
        self.request.errors.add('body', 'data', 'Can\'t update tender status')
        self.request.errors.status = 403
        return

    if self.request.authenticated_role == 'tender_owner' \
            and self.request.validated['tender_status'] == 'active.tendering':
        if 'tenderPeriod' in data and 'endDate' in data['tenderPeriod']:
            self.request.validated['tender'].tenderPeriod.import_data(data['tenderPeriod'])
            if calculate_business_date(get_now(), TENDERING_EXTRA_PERIOD, self.request.validated['tender']) > \
                    self.request.validated['tender'].tenderPeriod.endDate:
                self.request.errors.add('body', 'data', 'tenderPeriod should be extended by {0.days} days'.format(
                    TENDERING_EXTRA_PERIOD))
                self.request.errors.status = 403
                return
            self.request.validated['tender'].initialize()
            self.request.validated['data']["enquiryPeriod"] = self.request.validated[
                'tender'].enquiryPeriod.serialize()

    apply_patch(self.request, save=False, src=self.request.validated['tender_src'])
    if self.request.authenticated_role == 'chronograph':
        check_status(self.request)
    elif self.request.authenticated_role == 'tender_owner' and tender.status == 'active.tendering':
        tender.invalidate_bids_data()
    elif self.request.authenticated_role == 'tender_owner' and \
            self.request.validated['tender_status'] == 'active.pre-qualification' and \
            tender.status == "active.pre-qualification.stand-still":
        if all_bids_are_reviewed(self.request):
            tender.qualificationPeriod.endDate = calculate_business_date(get_now(), COMPLAINT_STAND_STILL,
                                                                         self.request.validated['tender'])
            tender.check_auction_time()
        else:
            self.request.errors.add('body', 'data', 'Can\'t switch to \'active.pre-qualification.stand-still\' while not all bids are qualified')
            self.request.errors.status = 403
            return
    elif self.request.authenticated_role == 'tender_owner' and \
            self.request.validated['tender_status'] == 'active.pre-qualification' and \
            tender.status != "active.pre-qualification.stand-still":
        self.request.errors.add('body', 'data', 'Can\'t update tender status')
        self.request.errors.status = 403
        return

    save_tender(self.request)
    self.LOGGER.info('Updated tender {}'.format(tender.id),
                     extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_patch'}))
    return {'data': tender.serialize(tender.status)}


def validate_unique_bids(bids):
    """ Return Bool
        True if number of unique identifier id biggest then MINIMAL_NUMBER_OF_BIDS
        else False
    """
    return len(set(bid['tenderers'][0]['identifier']['id'] for bid in bids)) >= MINIMAL_NUMBER_OF_BIDS


def check_initial_bids_count(request):
    tender = request.validated['tender']
    if tender.lots:
        [setattr(i.auctionPeriod, 'startDate', None) for i in tender.lots if i.numberOfBids < MINIMAL_NUMBER_OF_BIDS and i.auctionPeriod and i.auctionPeriod.startDate]
        for i in tender.lots:
            # gather all bids by lot id
            bids = [bid
                    for bid in tender.bids
                    if i.id in [i_lot.relatedLot for i_lot in bid.lotValues
                                if i_lot.status in ["active", "pending"]] and bid.status in ["active", "pending"]]

            if i.numberOfBids < MINIMAL_NUMBER_OF_BIDS or not validate_unique_bids(bids) and i.status == 'active':
                setattr(i, 'status', 'unsuccessful')
                for bid_index, bid in enumerate(tender.bids):
                    for lot_index, lot_value in enumerate(bid.lotValues):
                        if lot_value.relatedLot == i.id:
                            setattr(tender.bids[bid_index].lotValues[lot_index], 'status', 'unsuccessful')

        if not set([i.status for i in tender.lots]).difference(set(['unsuccessful', 'cancelled'])):
            LOGGER.info('Switched tender {} to {}'.format(tender.id, 'unsuccessful'),
                        extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_unsuccessful'}))
            tender.status = 'unsuccessful'
    elif tender.numberOfBids < MINIMAL_NUMBER_OF_BIDS or not validate_unique_bids(tender.bids):
        LOGGER.info('Switched tender {} to {}'.format(tender.id, 'unsuccessful'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_unsuccessful'}))
        tender.status = 'unsuccessful'


def validate_features_custom_weight(self, data, features, max_sum):
    if features and data['lots'] and any([
        round(vnmax([
            i
            for i in features
            if i.featureOf == 'tenderer' or i.featureOf == 'lot' and i.relatedItem == lot['id'] or i.featureOf == 'item' and i.relatedItem in [j.id for j in data['items'] if j.relatedLot == lot['id']]
        ]), 15) > max_sum
        for lot in data['lots']
    ]):
        raise ValidationError(u"Sum of max value of all features for lot should be less then or equal to {:.0f}%".format(max_sum * 100))
    elif features and not data['lots'] and round(vnmax(features), 15) > max_sum:
        raise ValidationError(u"Sum of max value of all features should be less then or equal to {:.0f}%".format(max_sum * 100))


def check_status(request):
    tender = request.validated['tender']
    now = get_now()

    if tender.status == 'active.tendering' and tender.tenderPeriod.endDate <= now and \
            not has_unanswered_complaints(tender) and not has_unanswered_questions(tender):
        for complaint in tender.complaints:
            check_complaint_status(request, complaint)
        LOGGER.info('Switched tender {} to {}'.format(tender['id'], 'active.pre-qualification'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_active.pre-qualification'}))
        tender.status = 'active.pre-qualification'
        tender.qualificationPeriod = type(tender).qualificationPeriod({'startDate': now})
        check_initial_bids_count(request)
        prepare_qualifications(request)
        return

    elif tender.status == 'active.pre-qualification.stand-still' and tender.qualificationPeriod and tender.qualificationPeriod.endDate <= now and not any([
        i.status in tender.block_complaint_status
        for q in tender.qualifications
        for i in q.complaints
    ]):
        LOGGER.info('Switched tender {} to {}'.format(tender['id'], 'active.stage2.pending'),
                    extra=context_unpack(request, {'MESSAGE_ID': 'switched_tender_active_stage2_pending'}))
        tender.status = 'active.stage2.pending'
        check_initial_bids_count(request)
        return


def set_ownership(item):
    item.owner_token = generate_id()


def prepare_shortlistedFirms(shortlistedFirms):
    """ Make list with keys
        key = {identifier_id}_{identifier_scheme}_{lot_id}
    """
    all_keys = set()
    for firm in shortlistedFirms:
        key = u"{firm_id}_{firm_scheme}".format(firm_id=firm['identifier']['id'],
                                                firm_scheme=firm['identifier']['scheme'])
        if firm.get('lots'):
            keys = set([u"{key}_{lot_id}".format(key=key, lot_id=lot['id']) for lot in firm.get('lots')])
        else:
            keys = set([key])
        all_keys |= keys
    return all_keys


def prepare_author(obj):
    """ Make key
        {author.identifier.id}_{author.identifier.scheme}
        or
        {author.identifier.id}_{author.identifier.scheme}_{lot.id}
        if obj has relatedItem and questionOf != tender or obj has relatedLot than
    """
    base_key = u"{id}_{scheme}".format(scheme=obj['author']['identifier']['scheme'],
                                       id=obj['author']['identifier']['id'])
    if obj.get('relatedLot') or (obj.get('relatedItem') and obj.get('questionOf') == 'lot'):
        base_key = u"{base_key}_{lotId}".format(base_key=base_key,
                                                lotId=obj.get('relatedLot') or obj.get('relatedItem'))
    return base_key


def prepare_bid_identifier(bid):
    """ Make list with keys
        key = {identifier_id}_{identifier_scheme}_{lot_id}
    """
    all_keys = set()
    for tenderer in bid['tenderers']:
        key = u"{id}_{scheme}".format(id=tenderer['identifier']['id'],
                                      scheme=tenderer['identifier']['scheme'])
        if bid.get('lotValues'):
            keys = set([u"{key}_{lot_id}".format(key=key,
                                                 lot_id=lot['relatedLot'])
                        for lot in bid.get('lotValues')])
        else:
            keys = set([key])
        all_keys |= keys
    return all_keys


def stage2_bid_post(self):
    tender = self.request.validated['tender']
    if self.request.validated['tender_status'] != 'active.tendering':
        self.request.errors.add('body', 'data', 'Can\'t add bid in current ({}) tender status'.format(
            self.request.validated['tender_status']))
        self.request.errors.status = 403
        return
    if tender.tenderPeriod.startDate and \
            get_now() < tender.tenderPeriod.startDate or \
            get_now() > tender.tenderPeriod.endDate:
        self.request.errors.add('body', 'data',
                                'Bid can be added only during the tendering period: from ({}) to ({}).'.format(
                                    tender.tenderPeriod.startDate, tender.tenderPeriod.endDate))
        self.request.errors.status = 403
        return
    bid = self.request.validated['bid']
    firm_keys = prepare_shortlistedFirms(tender.shortlistedFirms)
    bid_keys = prepare_bid_identifier(bid)
    if not (bid_keys <= firm_keys):
        self.request.errors.add('body', 'data', 'Firm can\'t create bid')
        self.request.errors.status = 403
        return
    if bid.status not in self.allowed_bid_status_on_create:
        self.request.errors.add('body', 'data',
                                'Bid can be added only with status: {}.'.format(self.allowed_bid_status_on_create))
        self.request.errors.status = 403
        return
    tender.modified = False
    api_set_ownership(bid, self.request)
    tender.bids.append(bid)
    if save_tender(self.request):
        self.LOGGER.info('Created tender bid {}'.format(bid.id),
                         extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_bid_create'},
                                              {'bid_id': bid.id}))
        self.request.response.status = 201
        self.request.response.headers['Location'] = self.request.route_url('{}:Tender Bids'.format(tender.procurementMethodType), tender_id=tender.id,
                                                                           bid_id=bid['id'])
        return {
            'data': bid.serialize('view'),
            'access': {
                'token': bid.owner_token
            }
        }
