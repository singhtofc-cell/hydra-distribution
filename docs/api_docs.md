# Hydra Trading System — API Documentation
# =========================================
# Signal Distribution API for Copy Trade System

## Base URL
```
http://localhost:8788
```

## Endpoints

### 🔵 Health Check
```
GET /health
```
Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "2h 15m 30s",
  "active_clients": 8,
  "total_signals_dispatched": 247
}
```

### 🔵 Send Signal
```
POST /api/v1/signal/send
```
Request Body:
```json
{
  "signal_type": "BUY",
  "priority": "URGENT",
  "symbol": "XAUUSD",
  "entry_price": 2350.50,
  "sl_price": 2330.00,
  "tp_prices": [2370.00, 2390.00, 2420.00],
  "lot_multiplier": 1.0,
  "risk_percent": 1.0,
  "source": "JUDAS_SWING",
  "grid_layer": 2,
  "expiry_minutes": 30
}
```
Response:
```json
{
  "success": true,
  "signal_id": "uuid-here",
  "message": "Signal dispatched to 8 clients",
  "dispatched_to": 8
}
```

### 🔵 Cancel Signal
```
POST /api/v1/signal/cancel/{signal_id}
```

### 🔵 Batch Send
```
POST /api/v1/signal/batch
```
Send multiple signals in one request.

### 🔵 Register Client
```
POST /api/v1/client/register
```

### 🔵 List Clients
```
GET /api/v1/client/list?status=ACTIVE
```

### 🔵 Update Client Status
```
PATCH /api/v1/client/{client_id}/status
```
Body: `{"status": "PAUSED"}`

### 🔵 Remove Client
```
DELETE /api/v1/client/{client_id}
```

### 🔵 Get Stats
```
GET /api/v1/stats
```

## Signal Types
| Type | Description |
|------|-------------|
| BUY | Long entry |
| SELL | Short entry |
| CLOSE_ALL | Close all positions |
| MODIFY_SL | Modify stop loss |
| PARTIAL_CLOSE | Partial position close |
| CANCEL | Cancel pending signal |

## Priority Levels
| Priority | Description |
|----------|-------------|
| NORMAL | Grid Layer 1-3 |
| URGENT | Judas Swing, Sweep Trap |
| EMERGENCY | News kill-switch, Risk alert |

## Client Currencies
- **USD**: Standard multiplier (1.0x)
- **USC**: Cent multiplier (100x)
