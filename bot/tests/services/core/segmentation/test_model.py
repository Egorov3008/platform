from services.core.segmentation.model import UserSegment


class TestUserSegment:
    def test_segment_values(self):
        assert UserSegment.NEW_USER.value == "new_user"
        assert UserSegment.ACTIVE_TRIAL.value == "active_trial"
        assert UserSegment.ACTIVE_PAID.value == "active_paid"
        assert UserSegment.EXPIRING_SOON.value == "expiring_soon"
        assert UserSegment.EXPIRED_PAID.value == "expired_paid"
        assert UserSegment.INACTIVE.value == "inactive"
        assert UserSegment.INACTIVE_TRIAL.value == "inactive_trial"
        assert UserSegment.CHURN_RISK.value == "churn_risk"
        assert UserSegment.COLD_LEAD.value == "cold_lead"
        assert UserSegment.BLOCKED.value == "blocked"

    def test_segment_uniqueness(self):
        values = [segment.value for segment in UserSegment]
        assert len(values) == len(set(values)), "Duplicate segment values found"

    def test_segment_membership(self):
        assert UserSegment.NEW_USER in UserSegment
        assert UserSegment.BLOCKED in UserSegment
        assert "new_user" in [s.value for s in UserSegment]
