from pydantic import BaseModel, EmailStr, Field


class DiscoverRequest(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)


class EmailCandidate(BaseModel):
    email: EmailStr
    pattern: str
    confidence: int = Field(ge=0, le=100)
    status: str


class DiscoverResponse(BaseModel):
    results: list[EmailCandidate]


class VerifyRequest(BaseModel):
    email: EmailStr


class VerifyResponse(BaseModel):
    email: EmailStr
    status: str
    confidence: int = Field(ge=0, le=100)
