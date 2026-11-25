from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

RelationshipType = Literal[
    "supports",
    "contradicts",
    "contextual",
]

HypothesisKey = Literal[
    "H1",
    "H2",
    "H3",
]

AnswerBasis = Literal[
    "source_supported",
    "hypothesis",
    "unknown",
]

GapType = Literal[
    "missing_record",
    "conflicting_information",
    "unverified_hypothesis",
    "insufficient_detail",
    "other",
]

GapPriority = Literal[
    "low",
    "medium",
    "high",
]


class HypothesisEvidenceProposal(BaseModel):
    """A proposed relationship between evidence and a hypothesis."""

    model_config = ConfigDict(extra="forbid")

    evidence_item_id: UUID
    relationship_type: RelationshipType
    rationale: str = Field(
        min_length=1,
        max_length=1500,
    )


class HypothesisProposal(BaseModel):
    """An AI-generated potential root cause."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=250,
    )
    description: str = Field(
        min_length=1,
        max_length=5000,
    )
    causal_mechanism: str | None
    evidence_links: list[HypothesisEvidenceProposal] = Field(
        max_length=20,
    )


class HypothesisGenerationOutput(BaseModel):
    """Structured output from root-cause hypothesis generation."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        min_length=1,
        max_length=3000,
    )
    hypotheses: list[HypothesisProposal] = Field(
        max_length=3,
    )
    warnings: list[str] = Field(
        max_length=50,
    )


class WhyStepProposal(BaseModel):
    """One step in a 5 Whys investigation."""

    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(
        ge=1,
        le=5,
    )
    question: str = Field(
        min_length=1,
        max_length=1000,
    )
    answer: str | None
    answer_basis: AnswerBasis
    evidence_item_id: UUID | None

    @model_validator(mode="after")
    def validate_evidence_basis(self):
        if self.answer_basis == "source_supported":
            if self.evidence_item_id is None:
                raise ValueError(
                    "A source-supported answer requires "
                    "an evidence item ID."
                )
            if self.answer is None or not self.answer.strip():
                raise ValueError(
                    "A source-supported answer requires an answer."
                )
        elif self.evidence_item_id is not None:
            raise ValueError(
                "Only source-supported answers may reference "
                "an evidence item."
            )
        return self


class EvidenceGapProposal(BaseModel):
    """An unresolved investigation information requirement."""

    model_config = ConfigDict(extra="forbid")

    gap_type: GapType
    description: str = Field(
        min_length=1,
        max_length=3000,
    )
    recommended_question: str | None
    priority: GapPriority


class HypothesisAnalysisProposal(BaseModel):
    """Detailed analysis for one generated hypothesis."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_key: HypothesisKey
    why_steps: list[WhyStepProposal] = Field(
        min_length=1,
        max_length=5,
    )
    evidence_gaps: list[EvidenceGapProposal] = Field(
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_step_sequence(self):
        step_numbers = [
            step.step_number
            for step in self.why_steps
        ]
        if len(step_numbers) != len(set(step_numbers)):
            raise ValueError(
                "Duplicate Why step numbers are not allowed."
            )
        if step_numbers != sorted(step_numbers):
            raise ValueError(
                "Why steps must be ordered sequentially."
            )
        return self


class RCAAnalysisDetailsOutput(BaseModel):
    """Structured output from detailed RCA investigation."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        min_length=1,
        max_length=5000,
    )
    analyses: list[HypothesisAnalysisProposal] = Field(
        max_length=3,
    )
    global_gaps: list[EvidenceGapProposal] = Field(
        max_length=30,
    )
    warnings: list[str] = Field(
        max_length=50,
    )


HYPOTHESIS_GENERATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
        },
        "hypotheses": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "causal_mechanism": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                    "evidence_links": {
                        "type": "array",
                        "maxItems": 20,
                        "items": {
                            "type": "object",
                            "properties": {
                                "evidence_item_id": {
                                    "type": "string",
                                },
                                "relationship_type": {
                                    "type": "string",
                                    "enum": [
                                        "supports",
                                        "contradicts",
                                        "contextual",
                                    ],
                                },
                                "rationale": {
                                    "type": "string",
                                },
                            },
                            "required": [
                                "evidence_item_id",
                                "relationship_type",
                                "rationale",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "title",
                    "description",
                    "causal_mechanism",
                    "evidence_links",
                ],
                "additionalProperties": False,
            },
        },
        "warnings": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "summary",
        "hypotheses",
        "warnings",
    ],
    "additionalProperties": False,
}


RCA_ANALYSIS_DETAILS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
        },
        "analyses": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "hypothesis_key": {
                        "type": "string",
                        "enum": ["H1", "H2", "H3"],
                    },
                    "why_steps": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_number": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 5,
                                },
                                "question": {
                                    "type": "string",
                                },
                                "answer": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "null"},
                                    ],
                                },
                                "answer_basis": {
                                    "type": "string",
                                    "enum": [
                                        "source_supported",
                                        "hypothesis",
                                        "unknown",
                                    ],
                                },
                                "evidence_item_id": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "null"},
                                    ],
                                },
                            },
                            "required": [
                                "step_number",
                                "question",
                                "answer",
                                "answer_basis",
                                "evidence_item_id",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "evidence_gaps": {
                        "type": "array",
                        "maxItems": 20,
                        "items": {
                            "type": "object",
                            "properties": {
                                "gap_type": {
                                    "type": "string",
                                    "enum": [
                                        "missing_record",
                                        "conflicting_information",
                                        "unverified_hypothesis",
                                        "insufficient_detail",
                                        "other",
                                    ],
                                },
                                "description": {
                                    "type": "string",
                                },
                                "recommended_question": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "null"},
                                    ],
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": [
                                        "low",
                                        "medium",
                                        "high",
                                    ],
                                },
                            },
                            "required": [
                                "gap_type",
                                "description",
                                "recommended_question",
                                "priority",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "hypothesis_key",
                    "why_steps",
                    "evidence_gaps",
                ],
                "additionalProperties": False,
            },
        },
        "global_gaps": {
            "type": "array",
            "maxItems": 30,
            "items": {
                "type": "object",
                "properties": {
                    "gap_type": {
                        "type": "string",
                        "enum": [
                            "missing_record",
                            "conflicting_information",
                            "unverified_hypothesis",
                            "insufficient_detail",
                            "other",
                        ],
                    },
                    "description": {
                        "type": "string",
                    },
                    "recommended_question": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                        ],
                    },
                },
                "required": [
                    "gap_type",
                    "description",
                    "recommended_question",
                    "priority",
                ],
                "additionalProperties": False,
            },
        },
        "warnings": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "summary",
        "analyses",
        "global_gaps",
        "warnings",
    ],
    "additionalProperties": False,
}
