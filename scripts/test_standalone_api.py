#!/usr/bin/env python3
"""
Smoke-test standalone Clients API на реальной панели 3x-ui v3.2.0 (Bearer token auth).
Запускай из корня проекта:
    cd /home/admin/platform && venv/bin/python scripts/test_standalone_api.py
"""
import asyncio
import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv("/home/admin/platform/.env")

BASE = os.getenv("XUI_API_URL", "").rstrip("/")
if not BASE.endswith("/panel"):
    BASE += "/panel"
TOKEN = os.getenv("XUI_TOKEN", "")

if not BASE or not TOKEN:
    print("❌ Укажи XUI_API_URL и XUI_TOKEN в .env")
    raise SystemExit(1)

TEST_INBOUND_IDS: list[int] = []


def _auth() -> dict:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
    }


class PanelTester:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)

    async def get_inbounds(self) -> list[int]:
        print("\n[1] GET /api/inbounds/list ...")
        r = await self.client.get(f"{BASE}/api/inbounds/list", headers=_auth())
        print(f"    status={r.status_code}")
        data = r.json()
        payload = data.get("obj", data)
        if not isinstance(payload, list):
            print(f"    unexpected body: {data}")
            return []
        ids = [i.get("id") for i in payload if i.get("id")]
        print(f"    found inbounds: {ids}")
        return ids

    async def add_client(self, inbound_ids: list[int]) -> str:
        email = f"test_{uuid.uuid4().hex[:8]}@smoke.test"
        client_id = str(uuid.uuid4())
        payload = {
            "client": {
                "id": client_id,
                "email": email,
                "limitIp": 2,
                "totalGB": 10737418240,
                "expiryTime": 0,
                "enable": True,
                "tgId": 0,
                "flow": "xtls-rprx-vision",
                "subId": email,
                "group": "",
                "comment": "smoke-test",
                "reset": 0,
            },
            "inboundIds": inbound_ids,
        }
        print(f"\n[2] POST /api/clients/add (email={email}) ...")
        r = await self.client.post(
            f"{BASE}/api/clients/add", headers=_auth(), json=payload
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")
        return email

    async def get_client(self, email: str) -> None:
        print(f"\n[3] GET /api/clients/get/{email} ...")
        r = await self.client.get(
            f"{BASE}/api/clients/get/{email}", headers=_auth()
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def attach(self, email: str, inbound_ids: list[int]) -> None:
        print(f"\n[4] POST /api/clients/{email}/attach {inbound_ids} ...")
        r = await self.client.post(
            f"{BASE}/api/clients/{email}/attach",
            headers=_auth(),
            json={"inboundIds": inbound_ids},
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def detach(self, email: str, inbound_ids: list[int]) -> None:
        print(f"\n[5] POST /api/clients/{email}/detach {inbound_ids} ...")
        r = await self.client.post(
            f"{BASE}/api/clients/{email}/detach",
            headers=_auth(),
            json={"inboundIds": inbound_ids},
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def update_client(self, email: str) -> None:
        print(f"\n[6] POST /api/clients/update/{email} ...")
        r = await self.client.post(
            f"{BASE}/api/clients/update/{email}",
            headers=_auth(),
            json={"email": email, "comment": "updated-by-smoke-test"},
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def reset_traffic(self, email: str) -> None:
        print(f"\n[7] POST /api/clients/resetTraffic/{email} ...")
        r = await self.client.post(
            f"{BASE}/api/clients/resetTraffic/{email}", headers=_auth()
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def delete_client(self, email: str) -> None:
        print(f"\n[8] POST /api/clients/del/{email} ...")
        r = await self.client.post(
            f"{BASE}/api/clients/del/{email}", headers=_auth()
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def onlines(self) -> None:
        print(f"\n[9] POST /api/clients/onlines ...")
        r = await self.client.post(
            f"{BASE}/api/clients/onlines", headers=_auth()
        )
        print(f"    status={r.status_code}")
        print(f"    body: {r.text[:400]}")

    async def run(self) -> None:
        try:
            inbound_ids = TEST_INBOUND_IDS or await self.get_inbounds()
            if not inbound_ids:
                print("\n❌ Нет inbound'ов для теста. Укажи TEST_INBOUND_IDS в скрипте.")
                return

            test_id = inbound_ids[0]
            email = await self.add_client([test_id])
            await self.get_client(email)
            if len(inbound_ids) >= 2:
                await self.attach(email, [inbound_ids[1]])
                await self.detach(email, [inbound_ids[1]])
            await self.update_client(email)
            await self.reset_traffic(email)
            await self.onlines()
            await self.delete_client(email)
            print("\n✅ Все endpoint'ы ответили. Проверь body на наличие {success:true}.")
        finally:
            await self.client.aclose()


if __name__ == "__main__":
    asyncio.run(PanelTester().run())
