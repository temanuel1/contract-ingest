from datetime import date
from pydantic import BaseModel, Field


class Renewal(BaseModel):
    non_renewal_notice_days: int = Field(
        description="The non-renewal notice of the term in days.", ge=0
    )
    renewal_term_months: int = Field(
        description="The renewal term length of the term in months.", gt=0
    )
    annual_escalator: float = Field(
        description="The annual escalator for the renewal of the term as a percentage.",
        ge=0,
        le=100,
    )


class Term(BaseModel):
    effective_date: date = Field(description="The effective date of the term.")
    billing_start_date: date = Field(description="The billing start date of the term.")
    billing_end_date: date = Field(description="The billing end date of the term.")
    term_length_months: int = Field(
        description="The length of the term in months.", gt=0
    )
    renewal: Renewal = Field(description="The details of the renewal of the term.")
