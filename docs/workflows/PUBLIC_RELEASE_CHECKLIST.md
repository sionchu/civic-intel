# Public release checklist

Run this checklist against the exact candidate commit before changing repository visibility.
It is a release gate, not a source-policy substitute.

## PRE-PUBLIC hard gates

Complete every gate in this section before changing repository visibility.

### Full remote history privacy

- mirror every remote ref and verify that no author or committer email is outside the intended public identities;
- verify `git ls-remote --heads --tags origin` has only the intended refs and tags; and
- after an approved rewrite, verify the replaced email is absent from every remote-reachable commit.

### Secret scan

- run an approved full-history secret scanner against the remote mirror;
- reject private keys, credentials, tokens, non-placeholder environment values and sensitive configuration paths; and
- verify `.env.example` contains only documented placeholders.

### License and external-data rights boundary

- verify root `LICENSE` remains Apache-2.0 and `NOTICE` remains present;
- verify provider data, disclosures and provider-derived fixture metadata are not presented as Apache-licensed; and
- review every live source against its `SourcePolicy` and the provider's current terms before collection, storage, display, AI use or commercial use.

### Workflow permissions

- verify workflow permissions are minimal and no workflow prints secrets or full environments;

### Tracked artifacts and blobs

- inspect all remote-reachable paths for credentials, unapproved binaries, archives, raw source payloads, private paths and unexpected large blobs; and
- run `git fsck --full --no-reflogs --no-progress` on the release mirror.

### Local full verification

- run the repository's full local Python, lint, type, quality and web verification; and
- record any remote CI runner/billing failure as `POST_PUBLIC_REQUIRED`, never as a successful CI result.

### Local HEAD == origin/master

- fetch and compare the intended local commit with `origin/master`;
- record the final commit SHA, remote branch/tag list and audit result; and
- change visibility only after every PRE-PUBLIC hard gate passes.

## POST-PUBLIC required gates

Complete every gate in this section immediately after changing repository visibility.

- rerun GitHub Actions;
- verify an actual CI-green result; a runner/billing block remains `POST_PUBLIC_REQUIRED` and is not a pass;
- clone the public repository into a fresh location and repeat the history/privacy audit; and
- verify the public repository exposes the intended `LICENSE`, `NOTICE` and README licensing boundary.

## Completed release record

The 2026-08-31 public-release verification completed for candidate
`fb67315394797f17164d144b5abfd625a5792099`:

- public visibility was confirmed;
- Verify run [33360331366](https://github.com/sionchu/civic-intel/actions/runs/33360331366),
  attempt 2, ran on a GitHub-hosted runner and completed successfully;
- a fresh unauthenticated public clone passed the reachable-history privacy, high-confidence
  secret, `git fsck`, artifact/blob, ref and document checks; and
- the public repository exposed `LICENSE`, `NOTICE` and the README licensing boundary.
