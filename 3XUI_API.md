# 3x-UI Panel API Documentation

> **Version:** `v3.2.0` (`MHSanaei/3x-ui` tag `v3.2.0`)  
> **Base URL:** `https://<host>:<port>/<base_path>/`  
> **Authentication:** Session Cookie (`session=...`) **or** Bearer Token (`Authorization: Bearer <token>`).

---

## Authentication

### Session Login (Cookie)

```http
POST /login
Content-Type: application/x-www-form-urlencoded
```

**Request body (form):**

| Field | Type | Required |
|---|---|---|
| `username` | string | ✅ |
| `password` | string | ✅ |
| `twoFactorCode` | string | if 2FA enabled |

**Response:**
```json
{
  "success": true,
  "msg": "Login successful"
}
```

On success the panel sets a `session` cookie. All subsequent API requests must include it:
```http
Cookie: session=<session_id>
```

> **Security note:** Unauthenticated requests to API paths return **404** (not 401) to hide endpoint existence.

### API Token (Bearer)

For programmatic access create an API token in panel settings, then send:

```http
Authorization: Bearer <api_token>
```

Token auth is enforced by `checkAPIAuth` middleware on all `/panel/api/*` routes.

---

## Inbounds API (`/panel/api/inbounds`)

### Read Operations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/list` | Get all inbounds with full client stats |
| `GET` | `/list/slim` | Get slim inbounds list (lighter payload) |
| `GET` | `/options` | Get inbound options (id, remark, tag, protocol, port, tlsFlowCapable) |
| `GET` | `/get/:id` | Get single inbound by ID |
| `GET` | `/:id/fallbacks` | Get fallback rules for inbound |

### Write Operations

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/add` | Create new inbound |
| `POST` | `/del/:id` | Delete inbound by ID |
| `POST` | `/update/:id` | Update inbound by ID |
| `POST` | `/setEnable/:id` | Toggle inbound enable/disable |
| `POST` | `/:id/resetTraffic` | Reset inbound traffic counters |
| `POST` | `/:id/delAllClients` | Delete all clients in an inbound |
| `POST` | `/resetAllTraffics` | Reset traffic for **all** inbounds |
| `POST` | `/import` | Import inbound from JSON string (form field `data`) |
| `POST` | `/:id/fallbacks` | Set fallback rules (atomic replace) |

### Request / Response Schemas

#### `POST /add` and `POST /update/:id`

**Request body** (`Inbound`):

```json
{
  "id": 0,
  "up": 0,
  "down": 0,
  "total": 0,
  "remark": "my-inbound",
  "enable": true,
  "expiryTime": 0,
  "trafficReset": "never",
  "lastTrafficResetTime": 0,
  "clientStats": [],
  "listen": "0.0.0.0",
  "port": 443,
  "protocol": "vless",
  "settings": "{\"clients\":[{\"id\":\"...\",\"email\":\"user@example.com\"}]}",
  "streamSettings": "{\"network\":\"ws\"...}",
  "tag": "inbound-443",
  "sniffing": "{\"enabled\":true}",
  "nodeId": null
}
```

> **Note on `settings` / `streamSettings` / `sniffing`:** In the database these are stored as **strings**, but the panel's custom `MarshalJSON` / `UnmarshalJSON` automatically converts them to/from `json.RawMessage` for the API. This means you can send them as either **JSON objects** or **JSON strings**.

**Response:**
```json
{
  "success": true,
  "msg": "Inbound added successfully",
  "obj": { /* created Inbound */ }
}
```

#### `POST /setEnable/:id`

**Request body:**
```json
{
  "enable": false
}
```

#### `POST /import`

**Form field:** `data` — JSON string or object of an `Inbound`. `Id` is reset to `0` automatically.

---

## Clients API (`/panel/api/clients`)

> This is the **new** canonical way to manage clients independently of inbounds. Inbound-embedded client operations (legacy) are listed at the end.

### Read Operations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/list` | List all clients with attachments & traffic |
| `GET` | `/list/paged` | Paginated list (see query params below) |
| `GET` | `/get/:email` | Get single client by email |
| `GET` | `/traffic/:email` | Get traffic stats for client |
| `GET` | `/subLinks/:subId` | Get subscription links by `subId` |
| `GET` | `/links/:email` | Get all connection links for client |

**Query params for `/list/paged`** (`ClientPageParams`):

| Param | Type | Description |
|---|---|---|
| `page` | int | Page number (default 1) |
| `pageSize` | int | Items per page (default 25, max 200) |
| `search` | string | Search term |
| `filter` | string | Filter key |
| `protocol` | string | Protocol filter |
| `inbound` | string | Inbound ID filter |
| `sort` | string | Sort field |
| `order` | string | Sort order (`asc`/`desc`) |
| `expiryFrom` | int64 | Expiry from timestamp |
| `expiryTo` | int64 | Expiry to timestamp |
| `usageFrom` | int64 | Usage from (bytes) |
| `usageTo` | int64 | Usage to (bytes) |
| `autoRenew` | string | Auto-renew filter |
| `hasTgID` | string | Has Telegram ID |
| `hasComment` | string | Has comment |
| `group` | string | Group name filter |

**Paged response** (`ClientPageResponse`):
```json
{
  "items": [ /* array of ClientSlim */ ],
  "total": 100,
  "filtered": 42,
  "page": 1,
  "pageSize": 25,
  "summary": {
    "total": 100,
    "active": 80,
    "online": ["user1@x.com"],
    "depleted": ["user2@x.com"],
    "expiring": ["user3@x.com"],
    "deactive": ["user4@x.com"]
  },
  "groups": ["group-a", "group-b"]
}
```

### Write Operations

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/add` | Create client |
| `POST` | `/update/:email` | Update client by email |
| `POST` | `/del/:email` | Delete client (query: `keepTraffic=1` to retain stats) |
| `POST` | `/:email/attach` | Attach client to inbounds |
| `POST` | `/:email/detach` | Detach client from inbounds |
| `POST` | `/resetAllTraffics` | Reset traffic for **all** clients |
| `POST` | `/delDepleted` | Delete all depleted clients |
| `POST` | `/bulkAdjust` | Bulk adjust expiry / quota |
| `POST` | `/bulkDel` | Bulk delete clients |
| `POST` | `/bulkCreate` | Bulk create clients |
| `POST` | `/bulkAttach` | Bulk attach to inbounds |
| `POST` | `/bulkDetach` | Bulk detach from inbounds |
| `POST` | `/bulkResetTraffic` | Bulk reset traffic |
| `POST` | `/resetTraffic/:email` | Reset traffic for one client |
| `POST` | `/updateTraffic/:email` | Manually set upload/download bytes |
| `POST` | `/ips/:email` | Get connected IP addresses |
| `POST` | `/clearIps/:email` | Clear stored IPs for client |
| `POST` | `/onlines` | Get currently online clients |
| `POST` | `/lastOnline` | Get last-seen timestamps |

### Request / Response Schemas

#### `POST /add`

**Request body** (`ClientCreatePayload`):
```json
{
  "client": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "security": "auto",
    "password": "uuid-or-password",
    "flow": "xtls-rprx-vision",
    "reverse": { "tag": "" },
    "auth": "",
    "email": "user@example.com",
    "limitIp": 2,
    "totalGB": 10737418240,
    "expiryTime": 0,
    "enable": true,
    "tgId": 123456789,
    "subId": "sub-abc-123",
    "group": "premium",
    "comment": "VIP user",
    "reset": 0
  },
  "inboundIds": [1, 2]
}
```

> **Note:** `id` is the UUID for VMess/VLESS. `tgId` is **int64** (not string). `reverse` is an object `{ "tag": "..." }` or omitted.

#### `POST /update/:email`

**Request body** (`Client`):
```json
{
  "email": "user@example.com",
  "limitIp": 3,
  "totalGB": 21474836480,
  "expiryTime": 1750000000000,
  "enable": true,
  "tgId": 123456789,
  "subId": "sub-abc-123",
  "group": "premium",
  "comment": "updated comment",
  "reset": 0
}
```

#### `POST /:email/attach` / `POST /:email/detach`

**Request body:**
```json
{
  "inboundIds": [1, 3]
}
```

#### `POST /bulkAdjust`

**Request body:**
```json
{
  "emails": ["a@x.com", "b@x.com"],
  "addDays": 30,
  "addBytes": 10737418240
}
```

#### `POST /bulkDel`

**Request body:**
```json
{
  "emails": ["a@x.com", "b@x.com"],
  "keepTraffic": false
}
```

**Response** (`BulkDeleteResult`):
```json
{
  "deleted": 2,
  "skipped": [
    {"email": "c@x.com", "reason": "not found"}
  ]
}
```

#### `POST /bulkCreate`

**Request body:** array of `ClientCreatePayload`.

#### `POST /updateTraffic/:email`

**Request body:**
```json
{
  "upload": 1048576,
  "download": 2097152
}
```

---

## Inbound-Embedded Client Operations (Legacy)

These endpoints manipulate clients **inside** a specific inbound. Used by older integrations and the 3x-UI web UI internally.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/panel/api/inbounds/addClient` | Add client to inbound (body: `Inbound` with client in `settings`) |
| `POST` | `/panel/api/inbounds/updateClient/:clientId` | Update client by `id`/`password`/`email` |
| `POST` | `/panel/api/inbounds/:id/delClient/:clientId` | Delete client from inbound by identifier |
| `POST` | `/panel/api/inbounds/:id/resetClientTraffic/:email` | Reset traffic for a client |
| `POST` | `/panel/api/inbounds/:id/delClientByEmail/:email` | Delete client by email |
| `POST` | `/panel/api/inbounds/resetAllClientTraffics/:id` | Reset all client traffics in inbound |
| `POST` | `/panel/api/inbounds/delDepletedClients/:id` | Delete depleted clients (`-1` for all inbounds) |
| `POST` | `/panel/api/inbounds/clientIps/:email` | Get client IPs |
| `POST` | `/panel/api/inbounds/clearClientIps/:email` | Clear client IPs |
| `POST` | `/panel/api/inbounds/onlines` | Get online client emails |
| `POST` | `/panel/api/inbounds/lastOnline` | Get last online data |
| `POST` | `/panel/api/inbounds/updateClientTraffic/:email` | Update client traffic manually |

> **Client identifiers:** Use `client.id` for VMess/VLESS, `client.password` for Trojan, or `client.email` for Shadowsocks.

---

## Server API (`/panel/api/server`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/status` | Server status (CPU, mem, disk, xray state) |
| `GET` | `/cpuHistory/:bucket` | CPU history buckets |
| `GET` | `/history/:metric/:bucket` | System metric history |
| `GET` | `/xrayMetricsState` | Current Xray metrics state |
| `GET` | `/xrayMetricsHistory/:metric/:bucket` | Xray metric history |
| `GET` | `/xrayObservatory` | Outbound observatory snapshot |
| `GET` | `/xrayObservatoryHistory/:tag/:bucket` | Observatory history for tag |
| `GET` | `/getXrayVersion` | Available Xray versions |
| `GET` | `/getPanelUpdateInfo` | Panel update info |
| `GET` | `/getConfigJson` | Current Xray `config.json` |
| `GET` | `/getDb` | Download `x-ui.db` (octet-stream) |
| `GET` | `/getNewUUID` | Generate new UUID |
| `GET` | `/getNewX25519Cert` | Generate X25519 cert |
| `GET` | `/getNewmldsa65` | Generate ML-DSA-65 key |
| `GET` | `/getNewmlkem768` | Generate ML-KEM-768 key |
| `GET` | `/getNewVlessEnc` | Generate VLESS encryption keys |
| `POST` | `/stopXrayService` | Stop Xray |
| `POST` | `/restartXrayService` | Restart Xray |
| `POST` | `/installXray/:version` | Install / update Xray version |
| `POST` | `/updatePanel` | Trigger panel self-update |
| `POST` | `/updateGeofile` | Update all geo files |
| `POST` | `/updateGeofile/:fileName` | Update specific geo file |
| `POST` | `/logs/:count` | Application logs (form: `level`, `syslog`) |
| `POST` | `/xraylogs/:count` | Xray logs (form: `filter`, `showDirect`, `showBlocked`, `showProxy`) |
| `POST` | `/importDB` | Import DB (`multipart/form-data`, file field `db`) |
| `POST` | `/getNewEchCert` | Generate ECH certificate (form: `sni`) |

---

## Data Models

### `Inbound`

```go
type Inbound struct {
    Id                   int                  `json:"id"`
    UserId               int                  `json:"-"`
    Up                   int64                `json:"up"`
    Down                 int64                `json:"down"`
    Total                int64                `json:"total"`
    Remark               string               `json:"remark"`
    Enable               bool                 `json:"enable"`
    ExpiryTime           int64                `json:"expiryTime"`
    TrafficReset         string               `json:"trafficReset"`  // "never" | "hourly" | "daily" | "weekly" | "monthly"
    LastTrafficResetTime int64                `json:"lastTrafficResetTime"`
    ClientStats          []xray.ClientTraffic `json:"clientStats"`
    Listen               string               `json:"listen"`
    Port                 int                  `json:"port"`
    Protocol             Protocol             `json:"protocol"`  // "vmess" | "vless" | "trojan" | "shadowsocks" | "wireguard" | "hysteria" | "http" | "mixed" | "tunnel"
    Settings             string               `json:"settings"`       // JSON string (auto-converted to object in API)
    StreamSettings       string               `json:"streamSettings"` // JSON string (auto-converted to object in API)
    Tag                  string               `json:"tag"`
    Sniffing             string               `json:"sniffing"`       // JSON string (auto-converted to object in API)
    NodeID               *int                 `json:"nodeId,omitempty"`
    FallbackParent       *FallbackParentInfo  `json:"fallbackParent,omitempty"`
}
```

### `FallbackParentInfo`

```json
{
  "masterId": 1,
  "path": "/fallback-path"
}
```

### `Client` (inbound-embedded schema)

```go
type Client struct {
    ID         string         `json:"id,omitempty"`       // UUID for VMess/VLESS
    Security   string         `json:"security"`
    Password   string         `json:"password,omitempty"` // Trojan password or SS key
    Flow       string         `json:"flow,omitempty"`
    Reverse    *ClientReverse `json:"reverse,omitempty"`  // { "tag": "..." }
    Auth       string         `json:"auth,omitempty"`     // Hysteria auth
    Email      string         `json:"email"`
    LimitIP    int            `json:"limitIp"`
    TotalGB    int64          `json:"totalGB"`
    ExpiryTime int64          `json:"expiryTime"`
    Enable     bool           `json:"enable"`
    TgID       int64          `json:"tgId"`               // NOTE: int64, not string!
    SubID      string         `json:"subId"`
    Group      string         `json:"group,omitempty"`
    Comment    string         `json:"comment"`
    Reset      int            `json:"reset"`
    CreatedAt  int64          `json:"created_at,omitempty"`
    UpdatedAt  int64          `json:"updated_at,omitempty"`
}
```

### `ClientReverse`

```json
{
  "tag": "reverse-proxy-tag"
}
```

### `ClientRecord` (database / standalone client)

Same fields as `Client` mapped to DB columns, plus:
- `Id int` — DB primary key
- `UUID string` (`json:"uuid"`) — stored in `uuid` column
- `Auth string`
- `Flow string`
- `Security string`
- `Reverse string` — stored as JSON string, custom marshal/unmarshal to/from `json.RawMessage`
- `CreatedAt int64` (`json:"createdAt"`)
- `UpdatedAt int64` (`json:"updatedAt"`)

### `ClientTraffic` (stats)

```go
type ClientTraffic struct {
    Email string `json:"email,omitempty"`
    Up    int64  `json:"up"`
    Down  int64  `json:"down"`
}
```

### `ClientWithAttachments`

```json
{
  "id": 1,
  "email": "user@x.com",
  "subId": "abc",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "password": "...",
  "auth": "",
  "flow": "xtls-rprx-vision",
  "security": "auto",
  "reverse": { "tag": "" },
  "limitIp": 2,
  "totalGB": 10737418240,
  "expiryTime": 0,
  "enable": true,
  "tgId": 123456,
  "group": "premium",
  "comment": "",
  "reset": 0,
  "createdAt": 0,
  "updatedAt": 0,
  "inboundIds": [1, 2],
  "traffic": {
    "email": "user@x.com",
    "up": 1048576,
    "down": 2097152
  }
}
```

### `InboundFallback`

```go
type InboundFallback struct {
    Id        int    `json:"id"`
    MasterId  int    `json:"masterId"`
    ChildId   int    `json:"childId"`
    Name      string `json:"name"`
    Alpn      string `json:"alpn"`
    Path      string `json:"path"`
    Dest      string `json:"dest"`
    Xver      int    `json:"xver"`
    SortOrder int    `json:"sortOrder"`
}
```

### `ClientGroup`

```json
{
  "id": 1,
  "name": "premium",
  "createdAt": 0,
  "updatedAt": 0
}
```

### `ClientInbound` (junction table)

```json
{
  "clientId": 1,
  "inboundId": 5,
  "flowOverride": "xtls-rprx-vision",
  "createdAt": 0
}
```

### `Node` (multi-node support)

```json
{
  "id": 1,
  "name": "node-1",
  "remark": "EU node",
  "scheme": "https",
  "address": "192.168.1.10",
  "port": 443,
  "basePath": "/panel",
  "apiToken": "...",
  "enable": true,
  "allowPrivateAddress": false,
  "status": "online",
  "lastHeartbeat": 0,
  "latencyMs": 12,
  "xrayVersion": "24.11.30",
  "panelVersion": "3.2.0",
  "cpuPct": 15.2,
  "memPct": 45.0,
  "uptimeSecs": 86400,
  "lastError": "",
  "inboundCount": 5,
  "clientCount": 120,
  "onlineCount": 45,
  "depletedCount": 3,
  "createdAt": 0,
  "updatedAt": 0
}
```

### `ApiToken`

```json
{
  "id": 1,
  "name": "my-token",
  "token": "...",
  "enabled": true,
  "createdAt": 0
}
```

---

## Python Quick-Start

```python
import requests

BASE = "https://tolko-dlya-svoih.ru:11283/60TXZUl9aUY8h130ng"
USERNAME = "RlXdWxUnaM"
PASSWORD = "bjRNLYHnnMOnzrd92Y"

session = requests.Session()
session.verify = False  # only if self-signed cert

# 1. Login
r = session.post(f"{BASE}/login", data={
    "username": USERNAME,
    "password": PASSWORD
})
r.raise_for_status()
print("Login:", r.json())

# 2. List inbounds
r = session.get(f"{BASE}/panel/api/inbounds/list")
print("Inbounds:", r.json())

# 3. Add client (standalone)
payload = {
    "client": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "newuser@example.com",
        "password": "550e8400-e29b-41d4-a716-446655440000",
        "flow": "xtls-rprx-vision",
        "limitIp": 2,
        "totalGB": 10737418240,
        "expiryTime": 0,
        "enable": True,
        "tgId": 0,
        "subId": "",
        "group": "",
        "comment": "",
        "reset": 0
    },
    "inboundIds": [1]
}
r = session.post(f"{BASE}/panel/api/clients/add", json=payload)
print("Add client:", r.json())

# 4. Get client traffic
r = session.get(f"{BASE}/panel/api/clients/traffic/newuser@example.com")
print("Traffic:", r.json())

# 5. Reset client traffic
r = session.post(f"{BASE}/panel/api/clients/resetTraffic/newuser@example.com")
print("Reset:", r.json())

# 6. Delete client
r = session.post(f"{BASE}/panel/api/clients/del/newuser@example.com")
print("Delete:", r.json())
```

---

## Important Integration Notes

1. **`settings` / `streamSettings` / `sniffing` serialization** — The panel stores these as strings internally, but the API automatically converts them to/from JSON objects. You can send them as either strings or objects.
2. **`trafficReset` is now a string** — Valid values: `"never"`, `"hourly"`, `"daily"`, `"weekly"`, `"monthly"`. Default is `"never"`.
3. **Client identifiers differ by protocol:**
   - **VMess / VLESS:** use `client.id` (UUID string)
   - **Trojan:** use `client.password`
   - **Shadowsocks:** use `client.email`
   - **Hysteria:** use `client.auth`
4. **`tgId` is int64** — Not a string. Use `0` for unset.
5. **`reverse` is an object** — `{ "tag": "..." }` or omitted/null. Not a plain string.
6. **Traffic units** are always **bytes** (`int64`).
7. **Timestamps** are Unix milliseconds (`expiryTime: 1750000000000`).
8. **Online checks** (`/onlines`, `/lastOnline`) operate on `email` as the primary key.
9. **WebSocket updates:** The panel broadcasts `inbounds` or `invalidate` events over WebSocket to connected UI sessions after any mutating operation.
10. **Fallbacks are now `MasterId`/`ChildId` based** — The old `Sni`-centric fallback model has been replaced with a parent/child relationship model.

---

## Postman Collection

Official reference maintained by the project author:  
[Postman – 3x-ui API](https://www.postman.com/hsanaei/3x-ui/collection/q1l5l0u/3x-ui)
