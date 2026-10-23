
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DisruptionType(str, Enum):
    CANCELLATION = "cancellation"
    DELAY = "delay"
    DENIED_BOARDING = "denied_boarding"
    DOWNGRADING = "downgrading"
    OTHER = "other"


class PassengerClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1, max_length=100)
    passenger_name: str = Field(min_length=1, max_length=150)
    airline: str = Field(min_length=1, max_length=150)

    flight_number: str = Field(min_length=1, max_length=30)
    departure_airport: str = Field(min_length=3, max_length=10)
    arrival_airport: str = Field(min_length=3, max_length=10)

    scheduled_departure: datetime
    disruption_type: DisruptionType

    notification_time: datetime | None = None
    actual_departure: datetime | None = None
    alternate_flight_taken: bool = False
    alternate_flight_delay_hours: float | None = Field(
        default=None, ge=0, le=168
    )

    description: str = Field(min_length=1, max_length=5000)
    evidence_references: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timeline(self):
        if (
            self.notification_time is not None
            and self.notification_time.tzinfo is not None
            and self.scheduled_departure.tzinfo is not None
            and self.notification_time > self.scheduled_departure
        ):
            raise ValueError(
                "Notification time cannot be after scheduled departure"
            )
        return self
