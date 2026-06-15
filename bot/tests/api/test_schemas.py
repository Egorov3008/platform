"""Tests for bot ↔ backend API DTOs.

Regression test for the referral DTO field-name mismatch:

- Backend endpoints ``GET/POST /api/v1/admin/referrals/links[...]`` return
  ``{"token": ..., "referrer_tg_id": ...}`` (the key name matches the
  ``referrer_tg_id`` column in DB and the ``ReferralLink`` dataclass).
- The bot-side ``ReferralLinkDTO`` originally declared an ``owner_tg_id``
  field, which caused ``Pydantic`` validation to fail at
  ``ReferralLinkDTO(**r.json())`` and broke the entire referral flow.
"""
from api.schemas import ReferralLinkDTO


class TestReferralLinkDTO:
    def test_parses_backend_response(self):
        """Backend returns ``referrer_tg_id`` — DTO must accept it."""
        payload = {
            "token": "ref_6436fbd878ab",
            "referrer_tg_id": 552810834,
        }
        dto = ReferralLinkDTO(**payload)
        assert dto.token == "ref_6436fbd878ab"
        assert dto.referrer_tg_id == 552810834

    def test_optional_fields_default(self):
        """``is_active`` and ``created_at`` are optional in some endpoints."""
        payload = {"token": "ref_abc", "referrer_tg_id": 1}
        dto = ReferralLinkDTO(**payload)
        assert dto.is_active is True
        assert dto.created_at is None

    def test_by_token_response_with_full_fields(self):
        """``GET /referrals/links/by-token/{token}`` returns id + created_at."""
        payload = {
            "token": "ref_xyz",
            "referrer_tg_id": 42,
            "created_at": "2026-06-15T16:38:41",
            "id": 7,
        }
        dto = ReferralLinkDTO(**payload)
        assert dto.token == "ref_xyz"
        assert dto.referrer_tg_id == 42
        assert dto.id == 7

    def test_null_token_from_get_endpoint(self):
        """Regression: ``GET /api/v1/admin/referrals/links/{tg_id}`` returns
        ``{"token": null, "referrer_tg_id": tg_id}`` for users who do not
        yet have a referral link (the endpoint signals "no link" via a
        null token instead of HTTP 404). The DTO must accept this — the
        dialog getter at ``dialogs/windows/getters/referral/main.py``
        handles the null case via ``if link and link.token:``.

        Previously ``token: str`` was required, which raised a
        ``ValidationError`` on every fresh user and produced noisy
        ``BackendAPIClient.get_referral_link failed`` ERROR log lines.
        """
        payload = {"token": None, "referrer_tg_id": 7563318767}
        dto = ReferralLinkDTO(**payload)
        assert dto.token is None
        assert dto.referrer_tg_id == 7563318767

    def test_omitted_token_defaults_to_none(self):
        """Omitting ``token`` is equivalent to passing ``None`` — the GET
        endpoint may return a body without a ``token`` key in some
        edge cases (e.g. older backend versions), and the DTO should
        not crash on that either."""
        dto = ReferralLinkDTO(referrer_tg_id=1)
        assert dto.token is None
        assert dto.referrer_tg_id == 1

    def test_attribute_access_matches_backend_contract(self):
        """The DTO must expose ``token`` and ``referrer_tg_id`` as attributes
        — getters in dialogs/windows/getters/referral/main.py and
        dialogs/windows/widgets/keybord/referral/main.py read them via
        ``link.token`` / ``link.get('token')`` / ``link['token']``.
        ``link.get('token')`` and ``link['token']`` only work on dicts;
        pydantic models support attribute access, so all three call sites
        must use ``link.token``. This test pins that contract.
        """
        payload = {"token": "ref_abc", "referrer_tg_id": 7}
        dto = ReferralLinkDTO(**payload)
        # Attribute access (the right pattern for pydantic models).
        assert dto.token == "ref_abc"
        assert dto.referrer_tg_id == 7
