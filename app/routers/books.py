from fastapi import APIRouter, Response

from app.database import database_connection
from app.models import BookInput, BookOut, BookUpdate
from app.services import BookService

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("", response_model=BookOut, status_code=201)
def create_book(body: BookInput):
    with database_connection() as connection:
        return BookService(connection).create(**body.model_dump())


@router.get("", response_model=list[BookOut])
def list_books(q: str | None = None, available_only: bool = False):
    with database_connection() as connection:
        return BookService(connection).list(q=q, available_only=available_only)


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    with database_connection() as connection:
        return BookService(connection).get(book_id)


@router.put("/{book_id}", response_model=BookOut)
def update_book(book_id: int, body: BookUpdate):
    with database_connection() as connection:
        return BookService(connection).update(book_id, **body.changes())


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int):
    with database_connection() as connection:
        BookService(connection).delete(book_id)
    return Response(status_code=204)