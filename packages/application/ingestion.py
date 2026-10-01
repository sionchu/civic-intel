from packages.application.acquisition import AcquisitionService
from packages.application.tracing import Trace, TraceSink
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceRunStatus
from packages.verification.policy import PolicyAction, require_policy


class SourceLifecycle:
    """The proven run/page/checkpoint lifecycle, composed with source-specific coverage."""

    def __init__(
        self,
        service: AcquisitionService,
        policy: SourcePolicy,
        *,
        error_summary: str,
        trace_sink: TraceSink | None = None,
    ):
        self.service = service
        self.policy = policy
        self.error_summary = error_summary
        self.trace = Trace(trace_sink)
        self.pages_committed = 0

    def load_checkpoint(self, feeder: str, scope_key: str):
        require_policy(self.policy, PolicyAction.FETCH)
        require_policy(self.policy, PolicyAction.STORE_METADATA)
        self.service.uows.assert_ready()
        return self.service.source_checkpoint(feeder, scope_key)

    def start(self, feeder: str, scope_key: str, metadata: dict | None = None):
        self._trace_context = self.trace.span("observe-source", root=True)
        self._trace_context.__enter__()
        try:
            with self.trace.span("policy-check"):
                require_policy(self.policy, PolicyAction.FETCH)
                require_policy(self.policy, PolicyAction.STORE_METADATA)
            with self.trace.span("start-run"):
                self.run = self.service.start_source_run(feeder, scope_key, metadata)
                self.trace.source_run_id = str(self.run.id)
            return self.run
        except Exception as exc:
            self._trace_context.__exit__(type(exc), exc, exc.__traceback__)
            raise

    def commit_page(self, **kwargs):
        if kwargs.get("run_id") != self.run.id:
            raise ValueError("page run does not match lifecycle")
        with self.trace.span("page-commit"):
            result = self.service.commit_source_page(**kwargs)
        self.pages_committed += 1
        return result

    def succeed(self):
        with self.trace.span("coverage-verified"):
            completed = self.service.finish_source_run(self.run.id, SourceRunStatus.SUCCESS)
        self._trace_context.__exit__(None, None, None)
        return completed

    def fail(self, exc: Exception) -> None:
        status = SourceRunStatus.PARTIAL if self.pages_committed else SourceRunStatus.FAILED
        try:
            with self.trace.span("finish-run"):
                self.service.finish_source_run(
                    self.run.id,
                    status,
                    error_code=type(exc).__name__[:120],
                    error_summary=self.error_summary,
                )
        finally:
            self._trace_context.__exit__(type(exc), exc, exc.__traceback__)
