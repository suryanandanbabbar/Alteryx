# Licensing Usage Test Database

This is a TEST-ONLY SQLite data source for exercising the existing
`UsageDataSource` abstraction for the Volume and Token Usage licensing
criteria.

## Seeded values

- `volume_usage.current_usage = 100`
- `token_usage.current_usage = 10000`

These are intentionally below the example limits:

- volume limit: 500
- token limit: 500000

## Tables

### `volume_usage`

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER | Fixed singleton row (`1`) |
| `current_usage` | INTEGER | Current cumulative volume |
| `updated_at` | TEXT | Last update timestamp |

### `token_usage`

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER | Fixed singleton row (`1`) |
| `current_usage` | INTEGER | Current cumulative token usage |
| `updated_at` | TEXT | Last update timestamp |

## Testing the boundary

Set volume to exactly `500`:

```sql
UPDATE volume_usage
SET current_usage = 500, updated_at = CURRENT_TIMESTAMP
WHERE id = 1;
```

The licensing criterion must fail because the existing rule is:

`current_usage >= signed_policy.limit`

Set token usage to exactly `500000`:

```sql
UPDATE token_usage
SET current_usage = 500000, updated_at = CURRENT_TIMESTAMP
WHERE id = 1;
```

The token criterion must fail for the same reason.

## Important architecture note

The production licensing package currently exposes the generic `UsageDataSource`
protocol and in-memory/callable implementations. It does not make SQLite a
production provider.

`sqlite_usage_source_test.py` is therefore a test-only adapter implementing
the existing protocol. It does not modify the production licensing package.

For end-to-end tests, inject:

- `SQLiteUsageDataSource(db_path, "volume_usage")` as `volume_usage_source`
- `SQLiteUsageDataSource(db_path, "token_usage")` as `token_usage_source`

The signed artifact policy remains the authority for whether each criterion is
enabled and what limit is enforced.
