from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class DiscoverRequest(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)


class EmailCandidate(BaseModel):
    email: EmailStr
    pattern: str
    confidence: int = Field(ge=0, le=100)
    status: Literal["verified", "risky", "invalid"]


class DiscoverResponse(BaseModel):
    results: list[EmailCandidate]


class VerifyRequest(BaseModel):
    email: EmailStr


class VerifyResponse(BaseModel):
    email: EmailStr
    status: Literal["verified", "risky", "invalid"]
    confidence: int = Field(ge=0, le=100)
