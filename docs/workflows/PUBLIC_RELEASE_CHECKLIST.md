# Public release checklist

Run this checklist against the exact candidate commit before changing repository visibility.
It is a release gate, not a source-policy substitute.

## History privacy

- mirror every remote ref and verify that no author or committer email is outside the intended public identities;
- verify `git ls-remote --heads --tags origin` has only the intended refs and tags; and
- after an approved rewrite, verify the replaced email is absent from every remote-reachable commit.

## Secrets

- run an approved full-history secret scanner against the remote mirror;
- reject private keys, credentials, tokens, non-placeholder environment values and sensitive configuration paths; and
- verify `.env.example` contains only documented placeholders.

## License and external data

- verify root `LICENSE` remains Apache-2.0 and `NOTICE` remains present;
- verify provider data, disclosures and provider-derived fixture metadata are not presented as Apache-licensed; and
- review every live source against its `SourcePolicy` and the provider's current terms before collection, storage, display, AI use or commercial use.

## Workflows and artifacts

- verify workflow permissions are minimal and no workflow prints secrets or full environments;
- require a successful CI run after the account runner/billing condition is resolved;
- inspect all remote-reachable paths for credentials, unapproved binaries, archives, raw source payloads, private paths and unexpected large blobs; and
- run `git fsck --full --no-reflogs --no-progress` on the release mirror.

## Remote release state

- fetch and compare the intended local commit with `origin/master`;
- record the final commit SHA, remote branch/tag list and audit result; and
- change visibility only after every preceding gate passes.
