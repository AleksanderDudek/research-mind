from enum import StrEnum


class SourceType(StrEnum):
    PDF   = "pdf"
    WEB   = "web"
    TEXT  = "text"
    AUDIO = "audio"
    IMAGE = "image"


class HistoryAction(StrEnum):
    SOURCE_ADDED   = "source_added"
    SOURCE_EDITED  = "source_edited"
    SOURCE_DELETED = "source_deleted"


class DetailLevel(StrEnum):
    QUICK    = "quick"
    STANDARD = "standard"
    DETAILED = "detailed"
