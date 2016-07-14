# -*- coding: utf-8 -*-
from openprocurement.api.utils import opresource
from openprocurement.tender.openeu.views.bid import TenderBidResource as BaseResourceEU
from openprocurement.tender.openua.views.bid import TenderBidResource as BaseResourceUA
from openprocurement.tender.competitivedialogue.models import STAGE_2_UA_TYPE, STAGE_2_EU_TYPE
from openprocurement.api.views.bid import TenderBidResource
from openprocurement.api.models import get_now
from openprocurement.api.utils import (
    save_tender,
    set_ownership,
    apply_patch,
    opresource,
    json_view,
    context_unpack,
)
from openprocurement.api.validation import (
    validate_bid_data,
    validate_patch_bid_data,
)


@opresource(name='Competitive Dialogue Stage2 EU Bids',
            collection_path='/tenders/{tender_id}/bids',
            path='/tenders/{tender_id}/bids/{bid_id}',
            procurementMethodType=STAGE_2_EU_TYPE,
            description="Competitive Dialogue  Stage2EU bids")
class CompetitiveDialogueStage2EUBidResource(BaseResourceEU):
    """ Tender Stage2 EU  bids """

    @json_view(content_type="application/json", permission='create_bid', validators=(validate_bid_data,))
    def collection_post(self):
        tender = self.request.validated['tender']
        if self.request.validated['tender_status'] != 'active.tendering':
            self.request.errors.add('body', 'data', 'Can\'t add bid in current ({}) tender status'.format(
                self.request.validated['tender_status']))
            self.request.errors.status = 403
            return
        if tender.tenderPeriod.startDate and get_now() < tender.tenderPeriod.startDate or get_now() > tender.tenderPeriod.endDate:
            self.request.errors.add('body', 'data',
                                    'Bid can be added only during the tendering period: from ({}) to ({}).'.format(
                                        tender.tenderPeriod.startDate, tender.tenderPeriod.endDate))
            self.request.errors.status = 403
            return
        print(tender.shortlistedFirms)

        bid = self.request.validated['bid']
        tender.modified = False
        set_ownership(bid, self.request)
        tender.bids.append(bid)
        if save_tender(self.request):
            self.LOGGER.info('Created tender bid {}'.format(bid.id),
                             extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_bid_create'},
                                                  {'bid_id': bid.id}))
            self.request.response.status = 201
            self.request.response.headers['Location'] = self.request.route_url('Tender Bids', tender_id=tender.id,
                                                                               bid_id=bid['id'])
            return {
                'data': bid.serialize('view'),
                'access': {
                    'token': bid.owner_token
                }
            }


@opresource(name='Competitive Dialogue Stage2 UA Bids',
            collection_path='/tenders/{tender_id}/bids',
            path='/tenders/{tender_id}/bids/{bid_id}',
            procurementMethodType=STAGE_2_UA_TYPE,
            description="Competitive Dialogue Stage2 UA bids")
class CompetitiveDialogueStage2UABidResource(BaseResourceUA):
    """ Tender Stage2 UA Stage2 bids """
    pass
