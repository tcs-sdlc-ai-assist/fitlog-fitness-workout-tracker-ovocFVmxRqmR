from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator


class UserCreate(BaseModel):
    display_name: str
    email: EmailStr
    username: str
    password: str
    confirm_password: str

    @field_validator("display_name")
    @classmethod
    def display_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name is required.")
        if len(v) > 100:
            raise ValueError("Display name must be 100 characters or fewer.")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Username is required.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(v) > 50:
            raise ValueError("Username must be 50 characters or fewer.")
        if not v.isalnum() and not all(c.isalnum() or c in ("_", "-") for c in v):
            raise ValueError("Username may only contain letters, numbers, hyphens, and underscores.")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password must be 128 characters or fewer.")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username is required.")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required.")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    email: str
    username: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("display_name")
    @classmethod
    def display_name_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Display name cannot be empty.")
            if len(v) > 100:
                raise ValueError("Display name must be 100 characters or fewer.")
        return v