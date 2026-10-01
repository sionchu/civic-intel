from packages.application.context import Application
from packages.persistence.database import Database

METHOD_GROUPS = {
    "start_source_run": "acquisition",
    "finish_source_run": "acquisition",
    "source_run": "acquisition",
    "source_runs": "acquisition",
    "source_checkpoint": "acquisition",
    "source_checkpoints": "acquisition",
    "feeder_observations": "acquisition",
    "feeder_observation_hash_manifest": "acquisition",
    "feeder_observation": "acquisition",
    "feeder_observation_contexts": "acquisition",
    "commit_source_page": "acquisition",
    "person_observation_links": "identity",
    "active_person_ids_by_observation": "identity",
    "materialize_feeder_observation": "identity",
    "assembly_base_profile_contexts": "profiles",
    "assembly_legislative_source_contexts": "profiles",
    "assembly_current_person_contexts": "profiles",
    "import_assembly_base_profile_claims": "profiles",
    "import_assembly_base_profile_claims_batch": "profiles",
    "import_assembly_legislative_claims_batch": "profiles",
    "identity_review_items": "review",
    "resolve_assembly_distinct_person_review": "review",
    "seed_golden": "onboarding",
    "import_reviewed_person": "onboarding",
    "import_organization_claim": "organizations",
    "import_organization_claim_pair": "organizations",
    "import_organization_claim_batch": "organizations",
    "import_organization_batch": "organizations",
    "reviewed_person_role_contexts": "public",
    "people": "public",
    "public_people": "public",
    "person_is_public": "public",
    "organizations": "public",
    "public_organizations": "public",
    "published_person_claim_contexts": "public",
    "published_organization_claim_contexts": "public",
    "person": "public",
    "organization": "public",
    "claims": "public",
    "evidence_for": "public",
    "sources": "public",
    "source": "public",
    "public_source": "public",
    "source_snapshot": "public",
    "policies": "public",
    "relationships": "public",
    "decision_episodes": "public",
    "operator_summary": "administration",
    "operator_records": "administration",
    "operator_record_detail": "administration",
    "prepare_work_order_references": "administration",
    "prepare_alio_person_materialization": "administration",
    "commit_alio_person_materialization": "administration",
    "prepare_nec_person_materialization": "administration",
    "commit_nec_person_materialization": "administration",
    "admin_preview": "administration",
    "admin_commit": "administration",
    "admin_evidence_options": "administration",
    "admin_queue": "administration",
    "admin_history": "administration",
    "admin_schema_ready": "administration",
}


class ScenarioDatabase(Database):
    def __setattr__(self, name, value):
        if name in METHOD_GROUPS and "application" in self.__dict__:
            setattr(getattr(self.application, METHOD_GROUPS[name]), name, value)
            return
        super().__setattr__(name, value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.application = Application(self)
        self.uows = self

    def __getattr__(self, name):
        if name in {
            "acquisition",
            "identity",
            "profiles",
            "review",
            "onboarding",
            "organizations",
            "public",
            "administration",
        }:
            return ScenarioService(getattr(self.application, name), self.application.public, name)
        if name == "materialize_feeder_observation":
            return self.materialize_and_publish_fixture
        if name in METHOD_GROUPS:
            return getattr(getattr(self.application, METHOD_GROUPS[name]), name)
        raise AttributeError(name)

    def materialize_and_publish_fixture(self, observation_id):
        from packages.application.publication import publish_claim

        result = self.application.identity.materialize_feeder_observation(observation_id)
        if result.claim_id is not None:
            publish_claim(self, result.claim_id)
        return result


class ScenarioService:
    def __init__(self, service, public, name):
        self.service, self.public, self.name = service, public, name

    def __getattr__(self, name):
        return getattr(self.service, name)

    def __call__(self, *args, **kwargs):
        return getattr(self.public, self.name)(*args, **kwargs)
