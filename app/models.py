import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ISBN_PATTERN = re.compile(r"^(\d{9}[\dX]|\d{13})$")


def _clean_isbn(value: str | None) -> str | None:
    if value is None:
        return value
    cleaned = re.sub(r"[-\s]", "", value).upper()
    if not _ISBN_PATTERN.match(cleaned):
        raise ValueError("ISBN must have 10 or 13 characters (hyphens allowed)")
    return cleaned


def _clean_email(value: str | None) -> str | None:
    if value is None:
        return value
    if not _EMAIL_PATTERN.match(value):
        raise ValueError("Invalid email address")
    return value.lower()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BookInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str
    total_copies: int = Field(ge=1, le=1000)

    @field_validator("isbn")
    @classmethod
    def _validate_isbn(cls, value):
        return _clean_isbn(value)


class BookUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    isbn: str | None = None
    total_copies: int | None = Field(default=None, ge=1, le=1000)

    @field_validator("isbn")
    @classmethod
    def _validate_isbn(cls, value):
        return _clean_isbn(value)

    @model_validator(mode="after")
    def _at_least_one_field(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Provide at least one field and do not send null values")
        return self

    def changes(self) -> dict:
        return self.model_dump(exclude_unset=True)


class StudentInput(StrictModel):
    student_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value):
        return _clean_email(value)


class StudentUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value):
        return _clean_email(value)

    @model_validator(mode="after")
    def _at_least_one_field(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Provide at least one field and do not send null values")
        return self

    def changes(self) -> dict:
        return self.model_dump(exclude_unset=True)


class BorrowInput(StrictModel):
    student_id: str = Field(min_length=1, max_length=20)
    book_id: int = Field(ge=1)
    days: int = Field(ge=1, le=30)


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    total_copies: int
    available_copies: int


class StudentOut(BaseModel):
    student_id: str
    name: str
    email: str


class LoanOut(BaseModel):
    id: int
    student_id: str
    student_name: str
    book_id: int
    book_title: str
    borrowed_date: str
    due_date: str
    returned_date: str | None
    fine: int
    is_overdue: bool