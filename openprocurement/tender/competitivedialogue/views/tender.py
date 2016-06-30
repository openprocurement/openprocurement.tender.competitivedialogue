# -*- coding: utf-8 -*-
from openprocurement.api.views.tender import TenderResource
from openprocurement.tender.openeu.views.tender import TenderEUResource
from openprocurement.tender.openua.validation import validate_patch_tender_ua_data
from openprocurement.tender.competitivedialogue.utils import patch_eu, set_ownership
from openprocurement.api.utils import opresource, json_view, save_tender, context_unpack
from openprocurement.tender.competitivedialogue.models import CD_EU_TYPE, CD_UA_TYPE, STAGE_2_EU_TYPE, STAGE_2_UA_TYPE


@opresource(name='Competitive Dialogue for EU procedure',
            path='/tenders/{tender_id}',
            procurementMethodType=CD_EU_TYPE,
            description="Open Contracting compatible data exchange format. See  for more info")
class CompetitiveDialogueEUResource(TenderEUResource):
    """ Resource handler for Competitive Dialogue EU"""

    @json_view(content_type="application/json", validators=(validate_patch_tender_ua_data,), permission='edit_tender')
    def patch(self):
        return patch_eu(self)


@opresource(name='Competitive Dialogue for UA procedure',
            path='/tenders/{tender_id}',
            procurementMethodType=CD_UA_TYPE,
            description="Open Contracting compatible data exchange format. See # for more info")
class CompetitiveDialogueUAResource(TenderResource):
    """ Resource handler for Competitive Dialogue UA"""

    @json_view(content_type="application/json", validators=(validate_patch_tender_ua_data,), permission='edit_tender')
    def patch(self):
        return patch_eu(self)


@opresource(name='Tender Stage 2 for UA procedure',
            path='/tenders/{tender_id}',
            procurementMethodType=STAGE_2_UA_TYPE,
            description="")
class TenderStage2UAResource(TenderResource):
    """ Resource handler for tender stage 2 UA"""

    @json_view(content_type="application/json", validators=(validate_patch_tender_ua_data,), permission='edit_tender')
    def patch(self):
        return patch_eu(self)


@opresource(name='Tender Stage 2 for EU procedure',
            path='/tenders/{tender_id}',
            procurementMethodType=STAGE_2_EU_TYPE,
            description="")
class TenderStage2UEResource(TenderResource):
    """ Resource handler for tender stage 2 EU"""

    @json_view(content_type="application/json", validators=(validate_patch_tender_ua_data,), permission='edit_tender')
    def patch(self):
        return patch_eu(self)


@opresource(name='Tender stage2 credentials',
                             path='/tenders/{tender_id}/credentials',
                             description="Tender stage2 credentials")
class TenderStage2CredentialsResource(TenderResource):
    def __init__(self, request, context):
        super(TenderStage2CredentialsResource, self).__init__(request, context)
        self.server = request.registry.couchdb_server

    @json_view(permission='generate_credentials')
    def patch(self):
        tender = self.request.validated['tender']
        if tender.status != "draft":
            self.request.errors.add('body', 'data',
                                    'Can\'t generate credentials in current ({}) contract status'.format(
                                        tender.status))
            self.request.errors.status = 403
            return

        set_ownership(tender, self.request)
        if save_tender(self.request):
            self.LOGGER.info('Generate Tender stage2 credentials {}'.format(tender.id),
                             extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_patch'}))
            return {
                'data': tender.serialize("view"),
                'access': {
                    'token': tender.owner_token
                }
            }