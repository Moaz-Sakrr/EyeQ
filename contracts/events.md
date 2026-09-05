# WebSocket event contract

Channel: `/ws/session/{session_id}`  ·  Auth: JWT in query param or header.

All frames are JSON: `{"type": "<name>", "data": {...}}`

| type | direction | data |
|---|---|---|
| `alert.raised` | server → client | `AlertPayload` |
| `alert.adjudicated` | server → client | `{alert_id, decision}` |
| `seat.state` | server → client | `{seat_id, cri, tier}` (throttled) |
| `session.ended` | server → client | `{session_id}` |
| `ping` / `pong` | both | `{}` |

## FR6 boundary
`alert.raised` carries no behavioral history. The client fetches history from
`GET /alerts/{alert_id}/history`, which returns **403** until an adjudication
exists for that alert.
