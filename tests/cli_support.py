import json


def cli_payload(output):
    receipt = json.loads(output)
    return receipt.get("result", receipt)


def explicit_cli_args(worker, argv):
    commit = "--commit" in argv
    if argv and argv[0] in {"observe", "inspect", "materialize", "publish", "review"}:
        return argv
    mapping = {
        "gukgam_reviewed_plan_import": ("observe", "gukgam-plan", "SOURCE_INGESTION"),
        "alio_reviewed_claim_import": ("publish", "alio-item12", "CLAIM_PUBLICATION"),
        "alio_current_executive_claim_import": ("publish", "alio-item4", "CLAIM_PUBLICATION"),
        "gukgam_reviewed_claim_import": ("publish", "gukgam-claim", "CLAIM_PUBLICATION"),
        "gukgam_reviewed_claim_batch_commit": ("publish", "gukgam-batch", "CLAIM_PUBLICATION"),
        "alio_safe_person_materialization": (
            "materialize",
            "alio-safe-people",
            "IDENTITY_MATERIALIZATION",
        ),
        "nec_safe_person_materialization": (
            "materialize",
            "nec-safe-people",
            "IDENTITY_MATERIALIZATION",
        ),
        "orggo_reviewed_organization_commit": (
            "materialize",
            "orggo-organizations",
            "IDENTITY_MATERIALIZATION",
        ),
    }
    verb, lane, effect = mapping[worker]
    if not commit:
        verb, effect = "inspect", "READ_ONLY"
    return [verb, lane, "--allow-effect", effect] + [x for x in argv if x != "--commit"]
