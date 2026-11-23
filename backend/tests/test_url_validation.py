import importlib
import sys
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from services.url_validation import is_google_maps_url

VALID = [
    "https://www.google.com/maps/place/Some+Pharmacy",
    "https://www.google.com/maps",
    "https://maps.google.com/?cid=123",
    "https://maps.google.com",
]

INVALID = [
    "https://www.google.com.evil.com/maps",
    "https://evil.com/www.google.com/maps",
    "https://evil.com/?u=https://www.google.com/maps",
    "https://www.google.com@evil.com/maps",
    "http://www.google.com/maps",
    "https://maps.google.com.evil.com",
    "https://www.google.com/mapsevil",
    "",
    "not a url",
]


@pytest.mark.parametrize("url", VALID)
def test_helper_accepts_valid(url):
    assert is_google_maps_url(url)


@pytest.mark.parametrize("url", INVALID)
def test_helper_rejects_spoofed(url):
    assert not is_google_maps_url(url)


@pytest.fixture
def routers(monkeypatch):
    for name in (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "N8N_WEBHOOK_SECRET",
        "GOSOM_API_URL",
    ):
        monkeypatch.setenv(name, "test")
    for name in (
        "supabase",
        "services.scraper",
        "services.narrative",
        "services.keybert_service",
        "services.sentiment",
    ):
        monkeypatch.setitem(sys.modules, name, MagicMock())
    for name in ("routers.automation", "routers.competitor"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    automation = importlib.import_module("routers.automation")
    competitor = importlib.import_module("routers.competitor")
    yield automation, competitor
    sys.modules.pop("routers.automation", None)
    sys.modules.pop("routers.competitor", None)


@pytest.mark.parametrize("model_name", ["automation:PharmacyUrlRequest", "competitor:CompetitorScrapeRequest"])
def test_request_models_validate(routers, model_name):
    module_name, class_name = model_name.split(":")
    module = routers[0] if module_name == "automation" else routers[1]
    model = getattr(module, class_name)
    for url in VALID:
        assert model(url=url).url == url
    for url in INVALID:
        with pytest.raises(ValidationError):
            model(url=url)
