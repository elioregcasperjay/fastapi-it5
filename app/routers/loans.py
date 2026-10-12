from typing import Literal

from fastapi import APIRouter

from app.database import database_connection
from app.models import BorrowInput, LoanOut
from app.services import LoanService

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.post("", response_model=LoanOut, status_code=201)
def borrow_book(body: BorrowInput):
    with database_connection() as connection:
        return LoanService(connection).borrow(**body.model_dump())


@router.post("/{loan_id}/return", response_model=LoanOut)
def return_book(loan_id: int):
    with database_connection() as connection:
        return LoanService(connection).return_book(loan_id)


@router.get("", response_model=list[LoanOut])
def list_loans(status: Literal["active", "returned", "overdue"] | None = None):
    with database_connection() as connection:
        return LoanService(connection).list(status=status)


@router.get("/{loan_id}", response_model=LoanOut)
def get_loan(loan_id: int):
    with database_connection() as connection:
        return LoanService(connection).get(loan_id)