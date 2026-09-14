# surge-shared-core

Shared Surge sections for Mac and iPhone.

## Scope

This repository is the single shared source for common Surge sections used by the LiangZhi home network profiles.

Current shared files:

- `Shared-Groups.dconf` — common `[Proxy Group]`
- `Shared-Rules.dconf` — common `[Rule]`

Platform-specific sections remain local on each device.

## Security boundary

Do **not** store any secrets or private infrastructure details here, including:

- subscription URLs
- node passwords or credentials
- Surge/WebUI passwords
- tracker passkeys
- complete unredacted logs
- private NAS host mappings or private IP mappings
- public IP addresses

Only sanitized, portable Surge sections may be committed.

## Change policy

Use minimal, precise changes. Validate syntax and expanded rule/group order before switching production profiles. Keep Mac- and iPhone-specific behavior outside the shared files.
