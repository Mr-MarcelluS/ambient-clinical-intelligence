from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Span(StrictModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    speaker: str
    timestamp: float | None = None


class Finding(StrictModel):
    id: str
    entity: str
    category: str
    polarity: Literal['positive', 'negative', 'uncertain']
    certainty: Literal['certain', 'uncertain']
    subject: str
    duration: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    temporality: str = 'unspecified'
    evidence: Span
    mention: Span


class Utterance(StrictModel):
    id: str
    section: Literal['S', 'O', 'A', 'P']
    evidence: Span


class Note(StrictModel):
    S: str
    O: str
    A: str
    P: str


class Warning(StrictModel):
    code: str
    reason: str
    severity: Literal['info', 'warning', 'error'] = 'warning'
    evidence: list[Span] = Field(default_factory=list)


class Analysis(StrictModel):
    transcript: str
    findings: list[Finding]
    utterances: list[Utterance]
    note: Note
    warnings: list[Warning]
    processing_seconds: float
    provider: str
    structured: dict = Field(default_factory=dict)


class ConsultationInput(StrictModel):
    transcript: str = Field(min_length=1, max_length=50000)
    synthetic_confirmed: Literal[True]
    title: str = Field(default='Fictional consultation', max_length=120)


class NoteUpdate(StrictModel):
    note: Note
    expected_version: int = Field(ge=1)


class Approval(StrictModel):
    expected_version: int = Field(ge=1)
    reviewer: str = Field(min_length=1, max_length=100)
    acknowledge_warnings: bool = False
    review_seconds: float = Field(ge=0)
