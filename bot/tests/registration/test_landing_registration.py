from registration.landing_registration import LandingRegistration


class TestLandingRegistration:
    async def test_can_handle_landing_token(self):
        reg = LandingRegistration()
        assert await reg.can_handle("landing_abc123def456") is True

    async def test_can_handle_rejects_other_tokens(self):
        reg = LandingRegistration()
        assert await reg.can_handle("gift_abc") is False
        assert await reg.can_handle("ref_xyz") is False
        assert await reg.can_handle("abc123") is False
        assert await reg.can_handle("") is False
        assert await reg.can_handle(None) is False  # type: ignore[arg-type]

    async def test_register_extracts_uid(self):
        reg = LandingRegistration()
        result = await reg.register("landing_abc123def456")
        assert result == {
            "success": True,
            "type": "landing",
            "landing_uid": "abc123def456",
            "is_registered": False,
        }