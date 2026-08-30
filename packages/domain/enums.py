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


class PublicationStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    PUBLISHED = "PUBLISHED"
    WITHHELD = "WITHHELD"


class RelationshipStrength(StrEnum):
    WEAK = "WEAK"
    STRONG = "STRONG"


class RelationshipEvidenceType(StrEnum):
    APPOINTMENT = "APPOINTMENT"
    CO_SERVICE = "CO_SERVICE"
    FINANCIAL = "FINANCIAL"
    FAMILY_PUBLIC_RECORD = "FAMILY_PUBLIC_RECORD"
    DIRECT_STATEMENT = "DIRECT_STATEMENT"
    CO_MENTION = "CO_MENTION"
