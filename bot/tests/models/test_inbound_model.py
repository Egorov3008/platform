from models.servers.inbound import Inbound


class TestInbound:
    def test_inbound_creation(self):
        inbound = Inbound(server_id=1, inbound_id=1, name_inbound="test-client")
        assert inbound.server_id == 1
        assert inbound.inbound_id == 1
        assert inbound.name_inbound == "test-client"

    def test_inbound_defaults(self):
        inbound = Inbound(server_id=1, inbound_id=1)
        assert inbound.name_inbound is None
