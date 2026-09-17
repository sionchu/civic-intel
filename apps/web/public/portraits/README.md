# Reviewed portrait assets

This directory contains only individually reviewed third-party media approved for the
bounded Portrait Pilot. Each asset is bound to a resolved canonical Person by the exact
`person_id` in `manifest.json`; the manifest is presentation metadata and is not an identity
authority or a source of canonical Person records.

Every asset requires an individual source file page, creator, license, attribution text,
revision timestamp, dimensions, byte size and SHA-1 review. `review_status` must remain
`ELIGIBLE` for the web to display the local asset. A changed revision, withdrawal, deletion or
rights change requires a new review before publication; an asset is removed or rendered with
the existing initials fallback while that review is pending.

The web serves the local reviewed copy at runtime. It does not fetch a remote portrait URL,
search Commons automatically, infer identity from a face, generate a likeness, or use a
portrait in directory search and filtering. Individual licensing terms govern each file;
the current pilot's attribution and license links are visible beside the image.
