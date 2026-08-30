from enum import StrEnum


class EpistemicStatus(StrEnum):
    FACT = "FACT"
    CLAIM = "CLAIM"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"
    ENTITY_UNRESOLVED = "ENTITY_UNRESOLVED"


class EvidenceStance(StrEnum):
    SUPPORT = "SUPPORT"
    REFUTE = "REFUTE"
    NEUTRAL = "NEUTRAL"


class SourceCollectionMode(StrEnum):
    API = "API"
    RSS = "RSS"
    HTTP = "HTTP"
    BROWSER = "BROWSER"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    BLOCKED = "BLOCKED"


class IdentityStatus(StrEnum):
    RESOLVED = "RESOLVED"
    REVIEW = "REVIEW"
    UNRESOLVED = "UNRESOLVED"


class RelationshipStrength(StrEnum):
    WEAK = "WEAK"
    STRONG = "STRONG"
