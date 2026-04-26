Plan: DatabaseSynchronizer Refactoring                                                                                                         │
│                                                                                                                                                │
│ Context                                                                                                                                        │
│                                                                                                                                                │
│ The DatabaseSynchronizer has two scenarios to handle:                                                                                          │
│ 1. Key not in cache + has tg_id from panel → add to DB and cache                                                                               │
│ 2. Key is in cache → update its data: used_traffic, limits (limit_ip, total_gb), expiry_time                                                   │
│                                                                                                                                                │
│ Current problem: _update_traffic_in_batches runs on ALL clients and returns False for any key if the HTTP subscription URL request fails —     │
│ meaning panel fields (expiry_time, limit_ip) also don't get updated even though they don't need HTTP. The update is fully blocked by HTTP      │
│ availability.                                                                                                                                  │
│                                                                                                                                                │
│ Goal: Decouple panel-data update (always) from traffic HTTP fetch (best-effort). Key updates succeed even when HTTP fails.                     │
│                                                                                                                                                │
│ ---                                                                                                                                            │
│ Changes                                                                                                                                        │
│                                                                                                                                                │
│ 1. services/synchron/cache_comparator.py                                                                                                       │
│                                                                                                                                                │
│ Add a get_present_keys() method that returns emails present in both panel and cache (intersection). This is used by DatabaseSynchronizer to    │
│ identify which keys need updating.                                                                                                             │
│                                                                                                                                                │
│ def get_present_keys(self) -> List[str]:                                                                                                       │
│     """Возвращает email ключей, присутствующих и в панели, и в кэше."""                                                                        │
│     return list(set(self.keys_panel) & set(self.keys_cache))                                                                                   │
│                                                                                                                                                │
│ Call order in sync_data: compare() sets out_keys/out_users → then call get_present_keys() to get update targets.                               │
│                                                                                                                                                │
│ ---                                                                                                                                            │
│ 2. services/synchron/traffic.py — TrafficUpdater                                                                                               │
│                                                                                                                                                │
│ Modify update_key_with_traffic to not require HTTP data for success:                                                                           │
│ - expiry_time, limit_ip, total_gb → always from client (panel data directly)                                                                   │
│ - used_traffic → from HTTP traffic_data if available, otherwise skip (don't block update)                                                      │
│ - Return True when panel fields saved, even if HTTP data is absent                                                                             │
│                                                                                                                                                │
│ async def update_key_with_traffic(self, pool, key, client, traffic_data=None) -> bool:                                                         │
│     try:                                                                                                                                       │
│         # Always update from panel client                                                                                                      │
│         key.expiry_time = client.expiry_time                                                                                                   │
│         key.limit_ip = client.limit_ip                                                                                                         │
│         key.total_gb = client.total_gb  # from panel, not HTTP header                                                                          │
│                                                                                                                                                │
│         # Best-effort: update used_traffic from HTTP                                                                                           │
│         if traffic_data:                                                                                                                       │
│             traffic_info = await self.parse_traffic_info(traffic_data)                                                                         │
│             if traffic_info:                                                                                                                   │
│                 key.used_traffic = traffic_info['used_bytes']                                                                                  │
│                                                                                                                                                │
│         await self.model_data.keys.update(pool, key, {"email": key.email})                                                                     │
│         return True                                                                                                                            │
│     except Exception as e:                                                                                                                     │
│         logger.error("Ошибка обновления ключа", email=key.email, error=str(e))                                                                 │
│         return False                                                                                                                           │
│                                                                                                                                                │
│ ---                                                                                                                                            │
│ 3. services/synchron/database_synchronizer.py — DatabaseSynchronizer                                                                           │
│                                                                                                                                                │
│ Rename _update_traffic_in_batches → _sync_existing_keys. Change signature to accept present_keys: List[str] (emails) + full client list. Build │
│  email→client map internally.                                                                                                                  │
│                                                                                                                                                │
│ Modify sync_data:                                                                                                                              │
│ out_keys, out_users = self.cache_comparator.compare()                                                                                          │
│ present_keys = self.cache_comparator.get_present_keys()  # NEW                                                                                 │
│                                                                                                                                                │
│ await self._restore_missing_data(clients, out_keys, out_users)                                                                                 │
│ stats = await self._sync_existing_keys(clients, present_keys, batch_size)  # RENAMED + NEW PARAM                                               │
│                                                                                                                                                │
│ _sync_existing_keys logic:                                                                                                                     │
│ 1. Build email→client map from clients                                                                                                         │
│ 2. Get server for subscription URL (still needed for HTTP traffic)                                                                             │
│ 3. Process present_keys in batches (not all clients like before):                                                                              │
│   - Fetch HTTP traffic batch (best-effort)                                                                                                     │
│   - For each email in batch, load key from cache                                                                                               │
│   - Call update_key_with_traffic(pool, key, client, traffic_data.get(email))                                                                   │
│   - Count successful/failed                                                                                                                    │
│                                                                                                                                                │
│ This filters to only update keys confirmed present in cache (not all panel clients).                                                           │
│                                                                                                                                                │
│ ---                                                                                                                                            │
│ 4. Tests — tests/services/synchron/test_database_synchronizer.py                                                                               │
│                                                                                                                                                │
│ Update affected tests:                                                                                                                         │
│ - test_sync_data_success — mock _sync_existing_keys instead of _update_traffic_in_batches                                                      │
│ - test_sync_data_empty_cache_data — same rename                                                                                                │
│ - Rename test_update_traffic_in_batches_* → test_sync_existing_keys_*                                                                          │
│ - Add test_sync_existing_keys_no_http_data — verifies update succeeds even with traffic_data=None                                              │
│ - Update conftest.py sample_client if needed (already has total_gb, limit_ip, expiry_time)                                                     │
│                                                                                                                                                │
│ Also update test_traffic.py: add test for update_key_with_traffic with traffic_data=None returning True (panel fields updated).                │
│                                                                                                                                                │
│ ---                                                                                                                                            │
│ Critical Files                                                                                                                                 │
│                                                                                                                                                │
│ - services/synchron/database_synchronizer.py — orchestrator, sync_data + _sync_existing_keys                                                   │
│ - services/synchron/cache_comparator.py — add get_present_keys()                                                                               │
│ - services/synchron/traffic.py — decouple HTTP from panel update in update_key_with_traffic                                                    │
│ - tests/services/synchron/test_database_synchronizer.py — update test names + add new test                                                     │
│ - tests/services/synchron/test_traffic.py — add test for no-HTTP update                                                                        │
│                                                                                                                                                │
│ ---                                                                                                                                            │
│ Verification                                                                                                                                   │
│                                                                                                                                                │
│ pytest tests/services/synchron/ -v                                                                                                             │
│                                                                                                                                                │
│ All 30 existing tests should pass. New test test_sync_existing_keys_no_http_data validates the core fix: key update succeeds even when         │
│ subscription URL is unreachable. 