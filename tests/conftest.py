import pytest


@pytest.fixture
def search_payload():
    """Real shape of a project-search response (probe 2026-07-26)."""
    return {
        "projects": [
            {
                "id": "83f2dccb-853a-4611-b3ae-4474423395c9",
                "title": {"de": "Wohnen am Stadtpark: Metallverkleidung", "en": "Metal cladding"},
                "projectNumber": "41694",
                "projectType": "tender",
                "projectSubType": "construction",
                "processType": "open",
                "lotsType": "without",
                "publicationId": "a3af4589-3fff-4ad6-abae-3179b12afd37",
                "publicationNumber": "41694-01",
                "pubType": "tender",
                "publicationDate": "2026-07-26",
                "procOfficeName": {"de": "Bereich Liegenschaften"},
                "lots": [],
                "orderAddress": {
                    "countryId": "CH",
                    "cantonId": "ZH",
                    "postalCode": "8952",
                    "city": {"de": "Schlieren"},
                },
            }
        ],
        "pagination": {"lastItem": "20260726|41694", "itemsPerPage": 20},
    }


@pytest.fixture
def detail_payload():
    return {
        "project-info": {
            "title": {"de": "Wohnen am Stadtpark: Metallverkleidung"},
            "processType": "open",
            "procOfficeAddress": {"name": {"de": "Bereich Liegenschaften"}},
        },
        "procurement": {
            "orderDescription": {"de": "Metallverkleidung Dachzentrale"},
            "processType": "open",
            "orderType": "construction_work",
            "additionalCpvCodes": [],
            "bkpCodes": [{"code": "215.2", "label": {"de": "Fassadenbau"}}],
            "npkCodes": [],
        },
        "dates": {"publicationDate": "2026-07-26", "offerDeadline": "2026-08-30"},
        "base": {
            "cpvCode": {"code": "45262650", "label": {"de": "Verblendungsarbeiten"}},
            "title": {"de": "Wohnen am Stadtpark"},
        },
        "hasProjectDocuments": True,
    }
