# Mac collector readiness, 2026-10-01

Status: PARTIAL. The dedicated installed runtime and offline fixtures are verified. SSD write
readiness and the live one-shot runner are not complete. This receipt records remote execution,
not live acquisition, publication, deployment or a source-rights grant.

## Immutable inputs and environment

- Code: `0ae694578125a9a070053205cf790880d9e07148`; documentation baseline `15b6d84`.
- Wheel: `civic_intel-0.1.0-py3-none-any.whl`, SHA-256
  `2c6cbf5e06ef16dafb3822eae431f918757ec67af28d343a2f441c560a37bcc4`.
- Transfer bundle: 354460 bytes, SHA-256
  `8a69956f15b2eccc3e5d72f81375b416c077b8b6ce586cd9a456e4c63171e356`.
- Bundle: wheel, exact pinned Alembic resources, 22 pinned runtime dependencies and hash manifest.
  No source credential, operational target, private data or live execution grant is included.
- Mac mini: macOS 26.5.2 (25F84), arm64, Python 3.12.14; Remote Desktop Commander 0.2.52.
- New internal runtime: `/Users/lee/Developer/civic-intel-collector-20261001`, mode 0700.
  Code/dependencies are prepared internally while the intended operational data target remains SSD.
- All remote operations used Remote Desktop Commander with an explicit Mac device and `/bin/zsh`.
  No Computer Use, alternative browser or remote-control transport was used.

## Executed verification

The preparation scripts below are saved under the runtime root. Processes were subsequently
checked for completion; an initial PID was never treated as a passing result.

| Command or check | Observed result |
|---|---|
| clean-environment Python `unpack.py` | Exit 0; remote transfer hash matched, 14 safe archive members extracted |
| clean-environment Python `setup.py` | Exit 0; 13 payload hashes matched, dedicated venv and 22 dependencies installed |
| venv `python -m pip --isolated --disable-pip-version-check check` | No broken requirements; exit 0 |
| venv `python verify_runtime.py` | Exit 0; disposable schema 0008→0007→0008 and missing-key audit passed |
| installed `civic inspect commands` | 37 explicit-effect routes, no worker/DB invocation |
| installed `civic observe assembly --allow-effect SOURCE_INGESTION --page-size 100 --database-url` with fixture URL and no key | Expected exit 1; canonical receipt validator passed |
| venv `python capture_isolation.py` invoking `sandbox-exec -f offline.sb …/probe_isolation.py` | Sandbox child exit 0; all six bounded checks passed |
| venv `python verify_isolated_cli.py` | Exit 0; 37-route inventory and actual installed missing-key acquisition audit passed inside sandbox |
| final release/manifest comparison | All 13 payload hashes still matched after tests |
| local `python -O .tools/prepare_mac_collection.py` with existing bundle | Expected exit 1 at explicit overwrite guard; wheel/bundle hashes unchanged |
| local `python -m packages.verification.architecture` | Exit 0; architecture-contract PASS |
| local `git diff --check` | Exit 0; no whitespace errors |

The missing-key audit established exactly one FAILED SourceRun per fresh fixture, sanitized
failure metadata, zero observations and no checkpoint. Source key absence fails before fetch;
the sandbox test additionally denied all network access. Fixture provisioning used Alembic
separately; acquisition startup did not create tables or migrate schema.

Six sandbox checks: controlled canary read outside runtime denied; canary write denied;
release write denied; localhost TCP connection denied with permission error; allowed fixture
write/read succeeded; release manifest read succeeded. These are bounded executed checks,
not comprehensive adversarial isolation evidence. File metadata is readable; allowed data
reads cover runtime and required OS/Homebrew resources. Writes are limited to fixtures/receipts.

Final offline profile SHA-256:
`cc21a341dca49bb2addf79c17d93dcb29d13c6ddba7dde0328accd38733223b5`.
Earlier profile attempts aborted before Python startup; crash reports showed the dyld ignition
path. Adding root-directory/boot-resource reads allowed the final profile to execute. The
observed correction is limited to this Mac; no OS security setting was changed. Apple's
[dyld source](https://github.com/apple-oss-distributions/dyld/blob/main/dyld/DyldProcessConfig.cpp)
describes the ignition shared-cache discovery path.

Remote receipts: `receipts/runtime-verification.json`, `receipts/isolation-verification.json`,
`receipts/isolated-cli-verification.json`, plus schema logs and canonical missing-key receipts.
No credential files were examined; no API key value was requested or printed.

## SSD and access findings

`/Volumes/data` is mounted APFS, advertised writable, approximately 2 TB. Synthesized container
disk4/volume disk4s1 maps to physical RTL9210 media disk6; the old Basic data partition name
does not change its APFS content identity. USB is now 10 Gb/s at location 0x01230000.
SMART is unsupported through this bridge; no drive-health PASS is claimed.

The owner confirms Finder can create folders. Remote Python mkdir stalled inside the mkdir
system call, and a subsequent bounded retry was killed after eight seconds without creating
`civic-intel`. Native Commander directory/write probes timed out; the 35-byte probe file was
absent on subsequent stat. The intended 8 MiB fsync/readback test never ran.
Only this task's stalled diagnostic processes and orphaned children were terminated; cleanup
was checked. Existing SSD data, formatting, mounting and USB state were preserved.

Initial narrow-window TCC queries did not establish a removable-volume denial. A subsequent
two-hour query found `AUTHREQ_PROMPTING` at 21:18:23.982 for request 448.99, service
`kTCCServiceSystemPolicyRemovableVolumes`, responsible executable `node`. No completed result
for that prompt appeared in the queried records. Preflight request 448.101 at 21:20:34 returned
authValue=1; this receipt does not interpret that internal value as an enabled/disabled setting.
An actual remote process ancestry check connected Python → node 6783 → node 4210 → PID 1110,
`npm exec @wonderwhy-er/desktop-commander@latest remote`, confirming the approval subject
belongs to the Commander's execution chain. This is a concrete access-prompt finding; current
checkbox state, visible prompt and the ultimate cause of the stall remain unverified.

Read-only SELECT of only removable-volume permission rows from the protected TCC database
returned authorization denied.
System Events UI-permission query returned AppleEvent timeout (-1712). Therefore the exact
Commander permission setting and cause of the write stall remain UNVERIFIED. A Files & Folders
Settings deep-link command completed; panel visibility was not inspected. The owner must
respond to the node-specific access prompt if it is present; see Apple's
[file access controls](https://support.apple.com/guide/mac-help/control-access-to-files-and-folders-on-mac-mchld5a35146/mac).

Remote Commander policy rejected the read-only `/sbin/mount` status query. That operation was
stopped without an alternative transport or a remount attempt. A prior `sudo pmset` change was
also rejected; no disk-sleep setting change is claimed.

## Remaining operational gate

1. Obtain the owner's response to node's access prompt, recheck SSD writes and execute the
   pending fsync/readback verification.
2. Allocate a fresh staging target with sole-writer ownership and schema 0008.
3. Prove bounded live egress, numeric rate/run budgets, cancellation/recovery and restricted
   credential delivery on fixtures. The current offline profile permits no live network traffic.
4. Obtain the exact SourcePolicy/source/scope/target grant before one live acquisition.

Prepared candidate: current unfiltered Assembly member roster; `national_assembly_members`,
`current_member_roster`, SourcePolicy `11000000-0000-0000-0000-000000000001`,
source contract `assembly_member_roster`, credential name `ASSEMBLY_API_KEY`. No resume,
identity materialization, Claim publication, admin write, deployment or scheduler is granted.
SourcePolicy has no revision field: use its ID, `terms_checked_at` 2026-08-30T00:00:00Z and
the pinned code/wheel to identify the reviewed policy.
The existing CLI's per-request timeout is 15 seconds; it has no enforced total request/page/run
budget or numeric throttle. No such enforcement is claimed by this preparation checkpoint.

Full product verification was not rerun for these documentation-only changes. The pinned code's
earlier canonical verification remains recorded in [the architecture receipt](architecture-current-master.md).
This checkpoint does not declare the Mac collector milestone complete.
