"""Typed orchestration failures."""


class OrchestrationError(RuntimeError):
    """Base class for deterministic runner errors."""


class InvalidTrackIdError(OrchestrationError):
    pass


class UnsafeArtifactPathError(OrchestrationError):
    pass


class UnknownArtifactTypeError(OrchestrationError):
    pass


class InvalidTransitionError(OrchestrationError):
    pass


class DecisionConflictError(OrchestrationError):
    pass


class UnexpectedHumanGateError(OrchestrationError):
    pass


class StepLimitExceededError(OrchestrationError):
    pass


class StepExecutionError(OrchestrationError):
    pass
