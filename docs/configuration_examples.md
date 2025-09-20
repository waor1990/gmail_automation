# Configuration Examples

The `config/gmail_config-final.json` file maps one or more senders to an
existing Gmail label. Start by copying the sample file at
`config/config-sample/gmail_config.sample.json` and adjust the entries to match
your workflow. Each label maps to a list of rule objects; every rule bundles
the senders that share the same behavior.

```json
{
  "SENDER_TO_LABELS": {
    "Finance": [
      {
        "read_status": false,
        "delete_after_days": 30,
        "emails": [
          "billing@example.com",
          "alerts@example.com"
        ]
      }
    ],
    "Newsletters": [
      {
        "read_status": true,
        "delete_after_days": null,
        "emails": [
          "news@example.com"
        ]
      }
    ]
  }
}
```

- `read_status` controls whether messages are marked as read after labeling.
- `delete_after_days` can be an integer or `null`. When set, messages older than
  the threshold are deleted after processing.
- `emails` lists every sender that should receive the same handling.

The automation normalizes string values such as `"true"`/`"false"` for
`read_status` and converts `delete_after_days` to integers. Labels referenced in
`SENDER_TO_LABELS` must already exist in Gmail; create them before running the
script or through the dashboard.

## Ignored email rules

Use the optional `IGNORED_EMAILS` section to define deterministic actions that
run before the standard labeling workflow. Each rule supports matching by sender
or domain along with a set of actions.

```json
{
  "IGNORED_EMAILS": [
    {
      "name": "Ignore alerts",
      "senders": ["alerts@example.com"],
      "actions": {
        "skip_analysis": true,
        "skip_import": true,
        "mark_as_read": true,
        "apply_labels": ["Ignored"],
        "archive": true,
        "delete_after_days": 0
      }
    }
  ]
}
```

- `skip_analysis` excludes matching addresses from dashboard comparisons.
- `skip_import` prevents `Import missing` from adding the address back into the
  config.
- `mark_as_read`, `apply_labels`, `archive`, and `delete_after_days` control how
  matching messages are handled in Gmail. Setting `delete_after_days` to `0`
  deletes matching mail immediately after the rule runs.
