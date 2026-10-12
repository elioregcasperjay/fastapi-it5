from fastapi import APIRouter, Response

from app.database import database_connection
from app.models import LoanOut, StudentInput, StudentOut, StudentUpdate
from app.services import LoanService, StudentService

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentOut, status_code=201)
def create_student(body: StudentInput):
    with database_connection() as connection:
        return StudentService(connection).create(**body.model_dump())


@router.get("", response_model=list[StudentOut])
def list_students(q: str | None = None):
    with database_connection() as connection:
        return StudentService(connection).list(q=q)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: str):
    with database_connection() as connection:
        return StudentService(connection).get(student_id)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(student_id: str, body: StudentUpdate):
    with database_connection() as connection:
        return StudentService(connection).update(student_id, **body.changes())


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: str):
    with database_connection() as connection:
        StudentService(connection).delete(student_id)
    return Response(status_code=204)


@router.get("/{student_id}/loans", response_model=list[LoanOut])
def list_student_loans(student_id: str):
    with database_connection() as connection:
        return LoanService(connection).for_student(student_id)