# Archived legacy `spec` tests

These tests were removed from active `unittest discover` after `pipelines/spec/` was deleted.
They are not mechanically migrated to `spec-v2` because `spec-v2` is not a 1:1 replacement for the old analytics `spec` pack:

- old tests assert pack-local `validate.py`, analytics `status.yaml` artifacts, write-feature cycle, and routing-state sync behavior from `pipelines/spec/`;
- current active runtime packs are `spec-v2` and `calibration`;
- making these tests pass by replacing `spec` with `spec-v2` would create false confidence.

To restore coverage, choose one explicit path:

1. create a test-only pack that preserves the old analytics contract and point these tests at it; or
2. expand `spec-v2` to own that contract, then migrate assertions deliberately; or
3. replace each archived test with a smaller test for the current `spec-v2` contract.

Files are stored as `*.py.disabled` so standard discovery does not run them accidentally.
