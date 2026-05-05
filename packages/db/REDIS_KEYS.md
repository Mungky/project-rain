# Redis Key Conventions — Project Rain

**Status:** Authoritative. All Redis keys MUST follow these conventions.
**Namespace:** Semua keys harus diawali dengan `rain:`.

---

## Session & State

| Key Pattern | Type | TTL | Description | Writer | Reader |
|-------------|------|-----|-------------|--------|--------|
| `rain:session:{user_id}` | String | 24h | Current user session blob (JSON) | Auth middleware | All endpoints |

## Cache

| Key Pattern | Type | TTL | Description | Writer | Reader |
|-------------|------|-----|-------------|--------|--------|
| `rain:cache:embed:{sha256}` | String | 7d | Embedding vector cache (JSON array) | DocumentService, ContextService | DocumentService, ContextService |
| `rain:cache:llm:{sha256}` | String | 1h | LLM response cache (JSON) | Chat orchestrator | Chat orchestrator |

## Agent / Work Mode (Phase 3)

| Key Pattern | Type | TTL | Description | Writer | Reader |
|-------------|------|-----|-------------|--------|--------|
| `rain:agent:run:{run_id}:state` | Hash | 1h | Work-mode runtime state | Work mode orchestrator | Work mode orchestrator |
| `rain:agent:run:{run_id}:queue` | List | 1h | Task queue for agent run | Planner | Worker agents |

## Distributed Locks

| Key Pattern | Type | TTL | Description | Writer | Reader |
|-------------|------|-----|-------------|--------|--------|
| `rain:lock:{resource}` | String | 30s | Distributed lock for critical sections | Any service | Any service |

---

## Notes

- **All keys MUST use the `rain:` prefix.** No exceptions.
- **TTL enforcement:** Redis is configured with `maxmemory-policy allkeys-lru`. Keys without TTL will be evicted under memory pressure. Always set TTL.
- **Key length:** Keep key names under 100 characters for performance.
- **Hash tags:** If clustering is added later, use `{user_id}` or `{run_id}` as the hash tag to ensure locality.
