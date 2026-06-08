"""Digitalization status constants and helpers."""
from __future__ import annotations


class Status:
    """File lifecycle statuses — a file is only digitalized when it reaches 'canonicalized' or beyond."""

    DISCOVERED = "discovered"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    EXTRACTION_FAILED = "extraction_failed"
    CANONICALIZING = "canonicalizing"
    CANONICALIZED = "canonicalized"
    VALIDATION_FAILED = "validation_failed"
    REGISTERED = "registered"
    CHUNKED = "chunked"
    INDEXED = "indexed"
    NEEDS_REVIEW = "needs_review"
    NEEDS_OCR = "needs_ocr"
    SKIPPED = "skipped"
    SKIPPED_UNSUPPORTED = "skipped_unsupported"

    _TERMINAL = frozenset({EXTRACTION_FAILED, VALIDATION_FAILED, SKIPPED, SKIPPED_UNSUPPORTED, NEEDS_OCR})
    _DIGITALIZED = frozenset({CANONICALIZED, REGISTERED, CHUNKED, INDEXED})

    @classmethod
    def is_terminal(cls, s: str) -> bool:
        return s in cls._TERMINAL

    @classmethod
    def is_digitalized(cls, s: str) -> bool:
        return s in cls._DIGITALIZED

    @classmethod
    def all_statuses(cls) -> list[str]:
        return [
            cls.DISCOVERED, cls.QUEUED, cls.EXTRACTING, cls.EXTRACTED,
            cls.EXTRACTION_FAILED, cls.CANONICALIZING, cls.CANONICALIZED,
            cls.VALIDATION_FAILED, cls.REGISTERED, cls.CHUNKED, cls.INDEXED,
            cls.NEEDS_REVIEW, cls.NEEDS_OCR, cls.SKIPPED, cls.SKIPPED_UNSUPPORTED,
        ]


class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
