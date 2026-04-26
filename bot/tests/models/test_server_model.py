from models.servers.server import Server


class TestServer:
    def test_server_creation(self):
        server = Server(
            id=1,
            cluster_name="Main Cluster",
            server_name="Main Server",
            api_url="http://localhost:54321",
            subscription_url="http://localhost:8000",
            login="admin",
            password="pass",
        )
        assert server.id == 1
        assert server.cluster_name == "Main Cluster"
        assert server.server_name == "Main Server"
        assert server.api_url == "http://localhost:54321"
        assert server.subscription_url == "http://localhost:8000"
        assert server.login == "admin"
        assert server.password == "pass"

    def test_server_defaults(self):
        server = Server(
            id=1,
            cluster_name="Test Cluster",
            server_name="Test Server",
            api_url="http://localhost:54321",
            subscription_url="http://localhost:8000",
            login="admin",
            password="pass",
        )
        assert server.id == 1
        assert server.cluster_name == "Test Cluster"
