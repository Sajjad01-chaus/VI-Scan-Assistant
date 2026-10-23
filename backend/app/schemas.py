from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Command(StrictModel):
    text: str = Field(min_length=1, max_length=4000)
    utterance_id: str = Field(min_length=1, max_length=100)
    context_version: int = Field(ge=0)
    intent: Literal['auto', 'dictate'] = 'auto'

class Selection(StrictModel):
    patient_id: str = Field(max_length=80)
    context_version: int = Field(ge=0)

class Finding(StrictModel):
    observation: str = Field(min_length=1, max_length=500)
    anatomical_site: str = Field(max_length=300)
    polarity: Literal['present', 'negated', 'unspecified']
    certainty: Literal['asserted', 'uncertain', 'not_definite']
    evidence: str = Field(min_length=1, max_length=1000)

class Extraction(StrictModel):
    findings: list[Finding] = Field(max_length=20)
    requires_clinician_review: Literal[True]

class DraftEdit(StrictModel):
    version: int = Field(ge=1)
    findings: list[Finding] = Field(max_length=20)

class Version(StrictModel):
    version: int = Field(ge=1)

class SpeechRequest(StrictModel):
    turn_id: str = Field(max_length=100)

class GroundedClaim(StrictModel):
    text: str = Field(min_length=1, max_length=1500)
    evidence: str = Field(min_length=1, max_length=1500)
    purpose: Literal['finding','limitation','next_step','cause']

class GroundedAnswer(StrictModel):
    claims: list[GroundedClaim] = Field(max_length=3)

class IdentityReply(StrictModel):
    decision: Literal['choose','unresolved']
    patient_name: str = Field(max_length=200)
