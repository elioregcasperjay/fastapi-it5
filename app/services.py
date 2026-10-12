from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from app.exceptions import BusinessRuleError, NotFoundError


def _to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


class BaseService:
    """Shared connection handling; subclasses implement _find and their own rules."""

    _label = "Record"

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        return _to_dict(self._conn.execute(sql, params).fetchone())

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        return [dict(row) for row in self._conn.execute(sql, params).fetchall()]

    def _find(self, key):
        raise NotImplementedError

    def get(self, key) -> dict:
        record = self._find(key)
        if record is None:
            raise NotFoundError(f"{self._label} '{key}' not found")
        return record

    @staticmethod
    def _today() -> date:
        return date.today()

    @staticmethod
    def _check_columns(changes: dict, allowed: set[str]) -> None:
        if not set(changes) <= allowed:
            raise ValueError("Unexpected column in update")


class BookService(BaseService):
    _label = "Book"
    _SELECT = "SELECT id, title, author, isbn, total_copies, available_copies FROM books"
    _UPDATABLE = {"title", "author", "isbn", "total_copies"}

    def _find(self, book_id: int) -> dict | None:
        return self._one(self._SELECT + " WHERE id = ?", (book_id,))

    def _isbn_taken(self, isbn: str, exclude_id: int | None = None) -> bool:
        row = self._one(
            "SELECT id FROM books WHERE isbn = ? AND id IS NOT ?", (isbn, exclude_id)
        )
        return row is not None

    def create(self, title: str, author: str, isbn: str, total_copies: int) -> dict:
        if self._isbn_taken(isbn):
            raise BusinessRuleError(f"A book with ISBN '{isbn}' already exists")
        cursor = self._conn.execute(
            "INSERT INTO books (title, author, isbn, total_copies, available_copies) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, author, isbn, total_copies, total_copies),
        )
        return self.get(cursor.lastrowid)

    def list(self, q: str | None = None, available_only: bool = False) -> list[dict]:
        sql = self._SELECT + " WHERE 1 = 1"
        params: list = []
        if q and q.strip():
            needle = q.strip().lower()
            sql += " AND (instr(lower(title), ?) > 0 OR instr(lower(author), ?) > 0)"
            params += [needle, needle]
        if available_only:
            sql += " AND available_copies > 0"
        return self._all(sql + " ORDER BY id", tuple(params))

    def update(self, book_id: int, **changes) -> dict:
        self._check_columns(changes, self._UPDATABLE)
        book = self.get(book_id)
        if "isbn" in changes and self._isbn_taken(changes["isbn"], exclude_id=book_id):
            raise BusinessRuleError(f"A book with ISBN '{changes['isbn']}' already exists")
        if "total_copies" in changes:
            on_loan = book["total_copies"] - book["available_copies"]
            if changes["total_copies"] < on_loan:
                raise BusinessRuleError(
                    f"Total copies cannot be below the {on_loan} copies currently on loan"
                )
            changes["available_copies"] = changes["total_copies"] - on_loan
        if changes:
            assignments = ", ".join(f"{column} = ?" for column in changes)
            self._conn.execute(
                f"UPDATE books SET {assignments} WHERE id = ?",
                (*changes.values(), book_id),
            )
        return self.get(book_id)

    def delete(self, book_id: int) -> None:
        self.get(book_id)
        if self._one("SELECT 1 AS x FROM loans WHERE book_id = ? LIMIT 1", (book_id,)):
            raise BusinessRuleError("Book has loan records and cannot be deleted")
        self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))


class StudentService(BaseService):
    _label = "Student"
    _SELECT = "SELECT student_id, name, email FROM students"
    _UPDATABLE = {"name", "email"}

    def _find(self, student_id: str) -> dict | None:
        return self._one(self._SELECT + " WHERE student_id = ?", (student_id,))

    def _email_taken(self, email: str, exclude_id: str | None = None) -> bool:
        row = self._one(
            "SELECT student_id FROM students WHERE email = ? AND student_id IS NOT ?",
            (email, exclude_id),
        )
        return row is not None

    def create(self, student_id: str, name: str, email: str) -> dict:
        if self._find(student_id) is not None:
            raise BusinessRuleError(f"Student ID '{student_id}' already exists")
        if self._email_taken(email):
            raise BusinessRuleError(f"Email '{email}' is already registered")
        self._conn.execute(
            "INSERT INTO students (student_id, name, email) VALUES (?, ?, ?)",
            (student_id, name, email),
        )
        return self.get(student_id)

    def list(self, q: str | None = None) -> list[dict]:
        sql = self._SELECT + " WHERE 1 = 1"
        params: list = []
        if q and q.strip():
            needle = q.strip().lower()
            sql += " AND (instr(lower(name), ?) > 0 OR instr(lower(student_id), ?) > 0)"
            params += [needle, needle]
        return self._all(sql + " ORDER BY student_id", tuple(params))

    def update(self, student_id: str, **changes) -> dict:
        self._check_columns(changes, self._UPDATABLE)
        self.get(student_id)
        if "email" in changes and self._email_taken(changes["email"], exclude_id=student_id):
            raise BusinessRuleError(f"Email '{changes['email']}' is already registered")
        if changes:
            assignments = ", ".join(f"{column} = ?" for column in changes)
            self._conn.execute(
                f"UPDATE students SET {assignments} WHERE student_id = ?",
                (*changes.values(), student_id),
            )
        return self.get(student_id)

    def delete(self, student_id: str) -> None:
        self.get(student_id)
        if self._one("SELECT 1 AS x FROM loans WHERE student_id = ? LIMIT 1", (student_id,)):
            raise BusinessRuleError("Student has loan records and cannot be deleted")
        self._conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))


class LoanService(BaseService):
    _label = "Loan"
    MAX_ACTIVE_LOANS = 3
    FINE_PER_DAY = 5
    _SELECT = (
        "SELECT l.id, l.student_id, s.name AS student_name, l.book_id, "
        "b.title AS book_title, l.borrowed_date, l.due_date, l.returned_date, l.fine "
        "FROM loans l "
        "JOIN students s ON s.student_id = l.student_id "
        "JOIN books b ON b.id = l.book_id"
    )

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self._students = StudentService(connection)
        self._books = BookService(connection)

    def _with_overdue(self, loan: dict | None) -> dict | None:
        if loan is not None:
            loan["is_overdue"] = (
                loan["returned_date"] is None
                and loan["due_date"] < self._today().isoformat()
            )
        return loan

    def _find(self, loan_id: int) -> dict | None:
        return self._with_overdue(self._one(self._SELECT + " WHERE l.id = ?", (loan_id,)))

    def _active_count(self, student_id: str) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM loans WHERE student_id = ? AND returned_date IS NULL",
            (student_id,),
        )
        return row["n"]

    def _insert_loan(self, student_id: str, book_id: int, borrowed: date, due: date) -> int:
        cursor = self._conn.execute(
            "INSERT INTO loans (student_id, book_id, borrowed_date, due_date) "
            "VALUES (?, ?, ?, ?)",
            (student_id, book_id, borrowed.isoformat(), due.isoformat()),
        )
        return cursor.lastrowid

    def _begin(self) -> None:
        # Take the write lock up front so the checks and writes cannot interleave.
        if not self._conn.in_transaction:
            self._conn.execute("BEGIN IMMEDIATE")

    def borrow(self, student_id: str, book_id: int, days: int) -> dict:
        self._begin()
        self._students.get(student_id)
        book = self._books.get(book_id)
        if book["available_copies"] < 1:
            raise BusinessRuleError(f"No copies of '{book['title']}' are available")
        held = self._one(
            "SELECT 1 AS x FROM loans WHERE student_id = ? AND book_id = ? "
            "AND returned_date IS NULL",
            (student_id, book_id),
        )
        if held:
            raise BusinessRuleError("Student already has this book on loan")
        if self._active_count(student_id) >= self.MAX_ACTIVE_LOANS:
            raise BusinessRuleError(
                f"Student already has {self.MAX_ACTIVE_LOANS} active loans"
            )
        today = self._today()
        self._conn.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
            (book_id,),
        )
        loan_id = self._insert_loan(student_id, book_id, today, today + timedelta(days=days))
        return self.get(loan_id)

    def return_book(self, loan_id: int) -> dict:
        self._begin()
        loan = self.get(loan_id)
        if loan["returned_date"] is not None:
            raise BusinessRuleError("Loan has already been returned")
        today = self._today()
        days_late = (today - date.fromisoformat(loan["due_date"])).days
        fine = max(0, days_late) * self.FINE_PER_DAY
        self._conn.execute(
            "UPDATE loans SET returned_date = ?, fine = ? WHERE id = ?",
            (today.isoformat(), fine, loan_id),
        )
        self._conn.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
            (loan["book_id"],),
        )
        return self.get(loan_id)

    def list(self, status: str | None = None) -> list[dict]:
        sql = self._SELECT
        params: tuple = ()
        if status == "active":
            sql += " WHERE l.returned_date IS NULL"
        elif status == "returned":
            sql += " WHERE l.returned_date IS NOT NULL"
        elif status == "overdue":
            sql += " WHERE l.returned_date IS NULL AND l.due_date < ?"
            params = (self._today().isoformat(),)
        elif status is not None:
            raise BusinessRuleError("Status must be active, returned, or overdue")
        rows = self._all(sql + " ORDER BY l.id", params)
        return [self._with_overdue(row) for row in rows]

    def for_student(self, student_id: str) -> list[dict]:
        self._students.get(student_id)
        rows = self._all(
            self._SELECT + " WHERE l.student_id = ? ORDER BY l.id", (student_id,)
        )
        return [self._with_overdue(row) for row in rows]