
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReporterType(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    PHARMACIST = "pharmacist"
    LITERATURE = "literature"


class PatientOutcome(str, Enum):
    RECOVERED = "recovered"
    RECOVERING = "recovering"
    NOT_RECOVERED = "not_recovered"
    DEATH = "death"
    UNKNOWN = "unknown"


class AdverseEventReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    case_id: Annotated[
        str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    ]
    drug_name: Annotated[str, Field(min_length=2, max_length=150)]
    reaction_description: Annotated[
        str, Field(min_length=5, max_length=3000)
    ]

    patient_age: Annotated[int, Field(ge=0, le=120)]
    reporter_type: ReporterType
    outcome: PatientOutcome
    event_onset_days: Annotated[int, Field(ge=0, le=36500)]

    hospitalization: bool
    death: bool

    @model_validator(mode="after")
    def validate_outcome_consistency(self):
        if self.death and self.outcome != PatientOutcome.DEATH:
            raise ValueError(
                "If death is true, outcome must be 'death'."
            )

        if self.outcome == PatientOutcome.DEATH and not self.death:
            raise ValueError(
                "If outcome is 'death', death must be true."
            )

        return self
