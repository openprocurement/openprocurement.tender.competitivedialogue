# -*- coding: utf-8 -*-
import os
import webtest
from hashlib import sha512
from datetime import datetime, timedelta
from uuid import uuid4
from copy import deepcopy
from openprocurement.api.tests.base import PrefixedRequestClass, test_organization
from openprocurement.api.utils import apply_data_patch
from openprocurement.api.models import get_now, SANDBOX_MODE
from openprocurement.tender.openeu.models import (TENDERING_DURATION, QUESTIONS_STAND_STILL,
                                                  COMPLAINT_STAND_STILL)

from openprocurement.tender.openua.tests.base import (test_tender_data as base_test_tender_data_ua)
from openprocurement.tender.openeu.tests.base import (test_tender_data as base_test_tender_data_eu,
                                                      test_features_tender_data,
                                                      test_bids,
                                                      test_bids as test_bids_eu, BaseTenderWebTest)
from openprocurement.tender.competitivedialogue.models import CD_EU_TYPE, CD_UA_TYPE, STAGE_2_EU_TYPE, STAGE_2_UA_TYPE

now = datetime.now()
test_tender_data_eu = deepcopy(base_test_tender_data_eu)
del test_tender_data_eu["minimalStep"]
test_tender_data_eu["procurementMethodType"] = CD_EU_TYPE
test_tender_data_ua = deepcopy(base_test_tender_data_eu)
del test_tender_data_ua["title_en"]
del test_tender_data_ua["minimalStep"]
test_tender_data_ua["procurementMethodType"] = CD_UA_TYPE
test_tender_data_ua["tenderPeriod"]["endDate"] = (now + timedelta(days=31)).isoformat()

# stage 2
test_tender_stage2_data_eu = deepcopy(base_test_tender_data_eu)
test_tender_stage2_data_ua = deepcopy(base_test_tender_data_ua)
test_tender_stage2_data_eu["procurementMethodType"] = STAGE_2_EU_TYPE
test_tender_stage2_data_ua["procurementMethodType"] = STAGE_2_UA_TYPE
test_tender_stage2_data_eu["procurementMethod"] = "selective"
test_tender_stage2_data_ua["procurementMethod"] = "selective"
test_shortlistedFirms = [
    {
        "lots": [{"id": uuid4().hex}],
        "identifier": test_organization["identifier"],
        "name": test_organization["name"]
    }
]
test_access_token_stage1 = uuid4().hex;
test_tender_stage2_data_eu["shortlistedFirms"] = test_shortlistedFirms
test_tender_stage2_data_ua["shortlistedFirms"] = test_shortlistedFirms
test_tender_stage2_data_eu["dialogue_token"] = sha512(test_access_token_stage1).hexdigest()
test_tender_stage2_data_ua["dialogue_token"] = sha512(test_access_token_stage1).hexdigest()
test_tender_stage2_data_ua["owner"] = "broker"
test_tender_stage2_data_eu["owner"] = "broker"
test_tender_stage2_data_ua["status"] = "draft"
test_tender_stage2_data_eu["status"] = "draft"


test_lots = [
    {
        'title': 'lot title',
        'description': 'lot description',
        'value': test_tender_data_eu['value']
    }
]


if SANDBOX_MODE:
    test_tender_data_eu['procurementMethodDetails'] = 'quick, accelerator=1440'
    test_tender_data_ua['procurementMethodDetails'] = 'quick, accelerator=1440'


class BaseCompetitiveDialogWebTest(BaseTenderWebTest):
    initial_data = None
    initial_status = None
    initial_bids = None
    initial_lots = None
    initial_auth = None

    def go_to_enquiryPeriod_end(self):
        now = get_now()
        self.set_status('active.tendering', {
            "enquiryPeriod": {
                "startDate": (now - timedelta(days=28)).isoformat(),
                "endDate": (now - (timedelta(minutes=1) if SANDBOX_MODE else timedelta(days=1))).isoformat()
            },
            "tenderPeriod": {
                "startDate": (now - timedelta(days=28)).isoformat(),
                "endDate": (now + (timedelta(minutes=2) if SANDBOX_MODE else timedelta(days=2))).isoformat()
            }
        })

    def setUp(self):
        self.app = webtest.TestApp(
            "config:tests.ini", relative_to=os.path.dirname(__file__))
        self.app.RequestClass = PrefixedRequestClass
        if self.initial_auth:
            self.app.authorization = self.initial_auth
        else:
            self.app.authorization = ('Basic', ('token', ''))
        self.couchdb_server = self.app.app.registry.couchdb_server
        self.db = self.app.app.registry.db

    def tearDown(self):
        del self.couchdb_server[self.db.name]

    def check_chronograph(self):
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        self.app.authorization = authorization
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

    def time_shift(self, status, extra=None):
        now = get_now()
        tender = self.db.get(self.tender_id)
        data = {}
        if status == 'enquiryPeriod_ends':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - timedelta(days=28)).isoformat(),
                    "endDate": (now - timedelta(days=1)).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - timedelta(days=28)).isoformat(),
                    "endDate": (now + timedelta(days=2)).isoformat()
                },
            })
        if status == 'active.pre-qualification':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION).isoformat(),
                    "endDate": (now).isoformat(),
                }
            })
        elif status == 'active.pre-qualification.stand-still':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION).isoformat(),
                    "endDate": (now).isoformat(),
                },
                "qualificationPeriod": {
                    "startDate": (now).isoformat(),
                },
            })
            if 'lots' in tender and tender['lots']:
                data['lots'] = []
                for index, lot in enumerate(tender['lots']):
                    lot_data = {'id': lot['id']}
                    if lot['status'] is 'active':
                        lot_data["auctionPeriod"] = {
                            "startDate": (now + COMPLAINT_STAND_STILL).isoformat()
                        }
                    data['lots'].append(lot_data)
            else:
                data.update({
                    "auctionPeriod": {
                        "startDate": (now + COMPLAINT_STAND_STILL).isoformat()
                    }
                })
        elif status == 'active.auction':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL - TENDERING_DURATION + QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL).isoformat()
                },
                "qualificationPeriod": {
                    "startDate": (now - COMPLAINT_STAND_STILL).isoformat(),
                    "endDate": (now).isoformat()
                }
            })
            if 'lots' in tender and tender['lots']:
                data['lots'] = []
                for index, lot in enumerate(tender['lots']):
                    lot_data = {'id': lot['id']}
                    if lot['status'] == 'active':
                        lot_data["auctionPeriod"] = {
                            "startDate": (now).isoformat()
                        }
                    data['lots'].append(lot_data)
            else:
                data.update({
                    "auctionPeriod": {
                        "startDate": now.isoformat()
                    }
                })
        elif status == 'complete':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat()
                },
                "auctionPeriod": {
                    "startDate": (now - timedelta(days=3)).isoformat(),
                    "endDate": (now - timedelta(days=2)).isoformat()
                },
                "awardPeriod": {
                    "startDate": (now - timedelta(days=1)).isoformat(),
                    "endDate": (now).isoformat()
                }
            })
            if self.initial_lots:
                data.update({
                    'lots': [
                        {
                            "auctionPeriod": {
                                "startDate": (now - timedelta(days=3)).isoformat(),
                                "endDate": (now - timedelta(days=2)).isoformat()
                            }
                        }
                        for i in self.initial_lots
                    ]
                })
        if extra:
            data.update(extra)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)

    def set_status(self, status, extra=None):
        data = {'status': status}
        if status == 'active.tendering':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - timedelta(days=1)).isoformat(),
                    "endDate": (now + TENDERING_DURATION - QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - timedelta(days=1)).isoformat(),
                    "endDate": (now + TENDERING_DURATION).isoformat()
                }
            })
        elif status == 'active.pre-qualification':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - timedelta(days=1)).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - timedelta(days=1)).isoformat(),
                    "endDate": (now).isoformat(),
                },
                "qualificationPeriod": {
                    "startDate": (now).isoformat(),
                }
            })
        elif status == 'active.pre-qualification.stand-still':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - timedelta(days=1)).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - timedelta(days=1)).isoformat(),
                    "endDate": (now).isoformat(),
                },
                "qualificationPeriod": {
                    "startDate": (now).isoformat(),
                },
                "auctionPeriod": {
                    "startDate": (now + COMPLAINT_STAND_STILL).isoformat()
                }
            })
        elif status == 'active.stage2.pending':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=1)).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL - TENDERING_DURATION + QUESTIONS_STAND_STILL).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=1)).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL).isoformat()
                },
                "qualificationPeriod": {
                    "startDate": (now - COMPLAINT_STAND_STILL).isoformat(),
                    "endDate": (now).isoformat()
                }
            })
            if self.initial_lots:
                data.update({
                    'lots': [
                        {
                            "auctionPeriod": {
                                "startDate": (now).isoformat()
                            }
                        }
                        for i in self.initial_lots
                        ]
                })
        elif status == 'active.awarded':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL - COMPLAINT_STAND_STILL - timedelta(days=2)).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL - timedelta(days=2)).isoformat()
                },
                "auctionPeriod": {
                    "startDate": (now - timedelta(days=2)).isoformat(),
                    "endDate": (now - timedelta(days=1)).isoformat()
                },
                "awardPeriod": {
                    "startDate": (now - timedelta(days=1)).isoformat(),
                    "endDate": (now).isoformat()
                }
            })
            if self.initial_lots:
                data.update({
                    'lots': [
                        {
                            "auctionPeriod": {
                                "startDate": (now - timedelta(days=2)).isoformat(),
                                "endDate": (now - timedelta(days=1)).isoformat()
                            }
                        }
                        for i in self.initial_lots
                    ]
                })
        elif status == 'complete':
            data.update({
                "enquiryPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=4)).isoformat(),
                    "endDate": (now - QUESTIONS_STAND_STILL - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat()
                },
                "tenderPeriod": {
                    "startDate": (now - TENDERING_DURATION - COMPLAINT_STAND_STILL - timedelta(days=4)).isoformat(),
                    "endDate": (now - COMPLAINT_STAND_STILL - timedelta(days=3)).isoformat()
                },
                # TODO: remove auctionPeriod, because we didn't have action in dialog
                "auctionPeriod": {
                    "startDate": (now - timedelta(days=3)).isoformat(),
                    "endDate": (now - timedelta(days=2)).isoformat()
                },
                "awardPeriod": {
                    "startDate": (now - timedelta(days=1)).isoformat(),
                    "endDate": (now).isoformat()
                }
            })
            if self.initial_lots:
                data.update({
                    'lots': [
                        {
                            "auctionPeriod": {
                                "startDate": (now - timedelta(days=3)).isoformat(),
                                "endDate": (now - timedelta(days=2)).isoformat()
                            }
                        }
                        for i in self.initial_lots
                    ]
                })
        if extra:
            data.update(extra)

        tender = self.db.get(self.tender_id)
        tender.update(apply_data_patch(tender, data))
        self.db.save(tender)

        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('chronograph', ''))
        # response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.app.authorization = authorization
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        return response


class BaseCompetitiveDialogEUWebTest(BaseCompetitiveDialogWebTest):
    initial_data = test_tender_data_eu


class BaseCompetitiveDialogUAWebTest(BaseCompetitiveDialogWebTest):
    initial_data = test_tender_data_ua


class BaseCompetitiveDialogEUStage2WebTest(BaseCompetitiveDialogWebTest):
    initial_data = test_tender_stage2_data_eu


class BaseCompetitiveDialogUAStage2WebTest(BaseCompetitiveDialogWebTest):
    initial_data = test_tender_stage2_data_ua


class BaseCompetitiveDialogUAContentWebTest(BaseCompetitiveDialogUAWebTest):
    initial_data = test_tender_data_ua
    initial_status = None
    initial_bids = None
    initial_lots = None

    def setUp(self):
        super(BaseCompetitiveDialogUAContentWebTest, self).setUp()
        self.create_tender()


class BaseCompetitiveDialogEUContentWebTest(BaseCompetitiveDialogEUWebTest):
    initial_data = test_tender_data_eu
    initial_status = None
    initial_bids = None
    initial_lots = None

    def setUp(self):
        super(BaseCompetitiveDialogEUContentWebTest, self).setUp()
        self.create_tender()


test_features_tender_eu_data = test_features_tender_data.copy()
test_features_tender_eu_data['procurementMethodType'] = CD_EU_TYPE
