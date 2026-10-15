"""Pydantic schemas: request validation + response shaping.

These models give us automatic input validation (the assignment's "input
validation" checklist item) and keep the API responses consistent.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# Lenient phone check: digits plus the usual separators, 7–20 chars.
_PHONE_RE = re.compile(r"^[0-9+\-()\s]{7,20}$")


def _clean_name(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("name must not be empty")
    return value.strip()


def _check_phone(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _PHONE_RE.match(value):
        raise ValueError("phone must be 7-20 chars (digits, spaces, +, -, () only)")
    return value


class StudentBase(BaseModel):
    name: str = Field(..., examples=["Asha Verma"])
    date_of_birth: date = Field(..., examples=["2004-06-15"])
    email: Optional[EmailStr] = Field(None, examples=["asha@example.com"])
    phone: Optional[str] = Field(None, examples=["+91 98765 43210"])
    course: Optional[str] = Field(None, examples=["Computer Science"])
    address: Optional[str] = Field(None, examples=["Pune, India"])
    enrollment_date: Optional[date] = Field(None, examples=["2023-08-01"])

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        return _clean_name(v)

    @field_validator("date_of_birth")
    @classmethod
    def _dob_in_past(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, v: Optional[str]) -> Optional[str]:
        return _check_phone(v)

    @model_validator(mode="after")
    def _require_contact(self):
        if not self.email and not self.phone:
            raise ValueError("provide at least one contact: email or phone")
        return self


class StudentCreate(StudentBase):
    """Payload for POST /students."""


class StudentUpdate(BaseModel):
    """Payload for PUT/PATCH /students/{id} — every field is optional.

    The 'at least one contact' rule is enforced in the endpoint, where we can
    merge the incoming changes with the stored record.
    """

    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        return _clean_name(v) if v is not None else v

    @field_validator("date_of_birth")
    @classmethod
    def _dob_in_past(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, v: Optional[str]) -> Optional[str]:
        return _check_phone(v)


class Student(StudentBase):
    """Response model — a stored student record."""

    id: int
    created_at: Optional[str] = None


class AskRequest(BaseModel):
    """Payload for the optional POST /ai/ask endpoint."""

    question: str = Field(..., min_length=1, examples=["How many students are there?"])
