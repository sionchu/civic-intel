# Change control

1. Confirm the governing product and role documents.
2. Extend canonical contracts in place; do not create parallel versioned schemas.
3. Add a forward and reversible Alembic migration for persistence changes.
4. Add deterministic contract, quality, API, and presentation regression coverage.
5. Review for dead fixture paths, duplicate semantics, privacy fields, and bypasses.
6. Run `make verify`, inspect the diff, and report local versus CI evidence accurately.
