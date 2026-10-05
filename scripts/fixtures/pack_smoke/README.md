# Pack smoke fixtures

Isolated minimal pipeline pack for compile validation (not installed under `pipelines/`).

Used by pack authoring and compile tests as an isolated minimal pack.

Copy layout matches `pipelines/<id>/` (graph, dispatch, status, registry).

Authoring JSON (same pack): `minimal/pack.json` — `--from-json` roundtrip.
`--init-pack` templates live in `pipeline_pack_authoring.py` (minimal is this
shape, parameterized). Playbook: `scripts/PIPELINE-PACK-AUTHORING.md`.
