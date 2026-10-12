# Library Book Borrowing System

A FastAPI + SQLite API that lets a school librarian manage books and students, and record borrowing and returning with due dates, late fines, and live copy counts.

## Setup (Windows, PowerShell)

```powershell
git clone <your-repo-url>
cd library_borrowing
```

With venv and pip:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

With uv:

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

If PowerShell blocks the activate script, run this once in the same window and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run

```powershell
uvicorn main:app --reload
```

If `uvicorn` is not recognized, use `python -m uvicorn main:app --reload`.

Open http://127.0.0.1:8000/docs to try every endpoint (click an endpoint, then Try it out). The database file `library.db` is created in the project folder on first start. To start from an empty database, stop the server and delete `library.db`.

## Project tree

```
main.py
requirements.txt
app/
  database.py      Database class (connection, schema)
  models.py        Pydantic models
  exceptions.py    NotFoundError, BusinessRuleError
  services.py      BaseService, BookService, StudentService, LoanService
  routers/
    books.py
    students.py
    loans.py
tests/
  test_services.py
  test_api.py
```

## Tests

```powershell
python -m unittest tests.test_services
python -m pip install httpx
python -m unittest tests.test_api
```

## Sample tests

Run them in order on an empty database, using the /docs page. Each step shows what to send and the output to expect. TODAY means today's date in YYYY-MM-DD form, and TODAY+7 means seven days later. Errors come back as `{"detail": "<message>"}`. Input mistakes come back as `{"detail": [ ... ]}` with a `loc` naming the bad field.

### Root

**1. GET /**

Expect: `{"message": "Welcome to the Library Book Borrowing System API"}`

### Books

**2. POST /books**

Body: `{"title": "Clean Code", "author": "Robert C. Martin", "isbn": "9780132350884", "total_copies": 2}`

Expect: `{"id": 1, "title": "Clean Code", "author": "Robert C. Martin", "isbn": "9780132350884", "total_copies": 2, "available_copies": 2}`

**3. POST /books (three more)**

Bodies, one at a time:
- `{"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "isbn": "9780135957059", "total_copies": 1}` gives id 2
- `{"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013593", "total_copies": 1}` gives id 3
- `{"title": "Refactoring", "author": "Martin Fowler", "isbn": "9780134757599", "total_copies": 1}` gives id 4

Each returns the book with `available_copies` equal to `total_copies`.

**4. POST /books (duplicate ISBN)**

Body: the same ISBN as step 2, `"isbn": "9780132350884"`.

Expect: `{"detail": "A book with ISBN '9780132350884' already exists"}`

**5. POST /books (invalid input)**

Body: `{"title": "X", "author": "Y", "isbn": "9780000000002", "total_copies": 0}`

Expect: `{"detail": [{"loc": ["body", "total_copies"], "msg": "Input should be greater than or equal to 1", ...}]}`

An unknown extra field, an empty title, or an ISBN like `abc` gives the same kind of error.

**6. GET /books**

Expect: a list of the 4 books, each with `available_copies` equal to `total_copies`.

**7. GET /books?q=clean**

Expect: `[{"id": 1, "title": "Clean Code", "author": "Robert C. Martin", "isbn": "9780132350884", "total_copies": 2, "available_copies": 2}]`

`GET /books?q=herbert` returns only Dune (author search).

**8. GET /books?available_only=true**

Expect: all 4 books for now. Repeat it after step 29.

**9. GET /books/1**

Expect: the Clean Code record from step 2.

`GET /books/99` expects `{"detail": "Book '99' not found"}`

**10. PUT /books/1**

Body: `{"title": "Clean Code, 2nd Printing"}`

Expect: `{"id": 1, "title": "Clean Code, 2nd Printing", "author": "Robert C. Martin", "isbn": "9780132350884", "total_copies": 2, "available_copies": 2}`

Body `{}` gives an input error (at least one field is required).

### Students

**11. POST /students**

Body: `{"student_id": "2026-0001", "name": "Ana Cruz", "email": "ana.cruz@um.edu.ph"}`

Expect: `{"student_id": "2026-0001", "name": "Ana Cruz", "email": "ana.cruz@um.edu.ph"}`

**12. POST /students (two more)**

Bodies, one at a time:
- `{"student_id": "2026-0002", "name": "Ben Reyes", "email": "ben.reyes@um.edu.ph"}`
- `{"student_id": "2026-0003", "name": "Cara Lim", "email": "cara.lim@um.edu.ph"}`

Each returns the student.

**13. POST /students (duplicates and bad input)**

- Body `{"student_id": "2026-0009", "name": "Dup", "email": "ana.cruz@um.edu.ph"}` expects `{"detail": "Email 'ana.cruz@um.edu.ph' is already registered"}`
- Body `{"student_id": "2026-0001", "name": "Dup", "email": "dup@um.edu.ph"}` expects `{"detail": "Student ID '2026-0001' already exists"}`
- Body with `"email": "not-an-email"` gives an input error naming `email`.

**14. GET /students?q=cruz**

Expect: `[{"student_id": "2026-0001", "name": "Ana Cruz", "email": "ana.cruz@um.edu.ph"}]`

`GET /students?q=0002` returns Ben (search by student ID). `GET /students` returns all 3.

**15. GET /students/2026-0001**

Expect: Ana's record.

`GET /students/nope` expects `{"detail": "Student 'nope' not found"}`

**16. PUT /students/2026-0001**

Body: `{"name": "Ana M. Cruz"}`

Expect: `{"student_id": "2026-0001", "name": "Ana M. Cruz", "email": "ana.cruz@um.edu.ph"}`

- Body `{"student_id": "x"}` gives an input error (student ID cannot change).
- Body `{"email": "ben.reyes@um.edu.ph"}` expects `{"detail": "Email 'ben.reyes@um.edu.ph' is already registered"}`

**17. DELETE /students/2026-0003**

Expect: an empty response (deleted). Repeating it expects `{"detail": "Student '2026-0003' not found"}`

### Borrowing

**18. POST /loans**

Body: `{"student_id": "2026-0001", "book_id": 1, "days": 7}`

Expect: `{"id": 1, "student_id": "2026-0001", "student_name": "Ana M. Cruz", "book_id": 1, "book_title": "Clean Code, 2nd Printing", "borrowed_date": "TODAY", "due_date": "TODAY+7", "returned_date": null, "fine": 0, "is_overdue": false}`

`GET /books/1` now shows `"available_copies": 1`.

**19. POST /loans (two more for Ana)**

Bodies, one at a time:
- `{"student_id": "2026-0001", "book_id": 2, "days": 7}` gives loan 2
- `{"student_id": "2026-0001", "book_id": 3, "days": 7}` gives loan 3

Ana now has 3 active loans.

**20. POST /loans (3-active-loans limit)**

Body: `{"student_id": "2026-0001", "book_id": 4, "days": 7}`

Expect: `{"detail": "Student already has 3 active loans"}`

**21. Rollback check**

`GET /books/4` still shows `"available_copies": 1`, and `GET /loans` still lists only 3 loans. The failed borrow saved nothing.

**22. POST /loans (same book twice)**

Body: `{"student_id": "2026-0001", "book_id": 1, "days": 7}`

Expect: `{"detail": "Student already has this book on loan"}`

**23. POST /loans (no copies left)**

Body: `{"student_id": "2026-0002", "book_id": 2, "days": 7}`

Expect: `{"detail": "No copies of 'The Pragmatic Programmer' are available"}`

**24. POST /loans (unknown student, unknown book, bad days)**

- `{"student_id": "nope", "book_id": 1, "days": 7}` expects `{"detail": "Student 'nope' not found"}`
- `{"student_id": "2026-0002", "book_id": 999, "days": 7}` expects `{"detail": "Book '999' not found"}`
- `"days": 0` or `"days": 31` gives an input error naming `days`.

**25. POST /loans (second copy of book 1 for Ben)**

Body: `{"student_id": "2026-0002", "book_id": 1, "days": 7}`

Expect: loan 4 for Ben. `GET /books/1` now shows `"available_copies": 0`.

### Books again (rules with loans)

**26. PUT /books/1 (total copies below copies on loan)**

Body: `{"total_copies": 1}`

Expect: `{"detail": "Total copies cannot be below the 2 copies currently on loan"}`

**27. PUT /books/1 (raise total copies)**

Body: `{"total_copies": 5}`

Expect: `{"id": 1, "title": "Clean Code, 2nd Printing", "author": "Robert C. Martin", "isbn": "9780132350884", "total_copies": 5, "available_copies": 3}`

**28. Delete protection**

- `DELETE /books/1` expects `{"detail": "Book has loan records and cannot be deleted"}`
- `DELETE /students/2026-0001` expects `{"detail": "Student has loan records and cannot be deleted"}`

**29. GET /books?available_only=true**

Expect: only books 1 (`"available_copies": 3`) and 4 (`"available_copies": 1`).

### Loan lookups

**30. GET /loans and its filters**

- `GET /loans` returns loans 1 to 4.
- `GET /loans?status=active` returns loans 1 to 4.
- `GET /loans?status=returned` returns `[]`.
- `GET /loans?status=overdue` returns `[]`.
- `GET /loans?status=bogus` gives an input error naming `status`.

**31. GET /loans/1**

Expect: the loan from step 18, showing `"book_title": "Clean Code, 2nd Printing"` and `"student_name": "Ana M. Cruz"`.

`GET /loans/999` expects `{"detail": "Loan '999' not found"}`

**32. GET /students/2026-0001/loans**

Expect: a list of 3 loans (ids 1, 2, 3) whose `book_title` values are "Clean Code, 2nd Printing", "The Pragmatic Programmer", and "Dune".

`GET /students/nope/loans` expects `{"detail": "Student 'nope' not found"}`

### Returning

**33. POST /loans/1/return**

Expect: `{"id": 1, "student_id": "2026-0001", "student_name": "Ana M. Cruz", "book_id": 1, "book_title": "Clean Code, 2nd Printing", "borrowed_date": "TODAY", "due_date": "TODAY+7", "returned_date": "TODAY", "fine": 0, "is_overdue": false}`

`GET /books/1` now shows `"available_copies": 4`.

**34. Return errors**

- `POST /loans/1/return` again expects `{"detail": "Loan has already been returned"}`
- `POST /loans/999/return` expects `{"detail": "Loan '999' not found"}`

**35. Status filters after a return**

`GET /loans?status=returned` returns only loan 1. `GET /loans?status=active` returns loans 2, 3 and 4.

### Late return with a fine

**36. Backdate loan 2 by 3 days**

There is no endpoint for this, so change the date in the database. Stop the server first (Ctrl+C), then in the project folder open Python and type these lines one at a time:

```powershell
python
```

```python
import sqlite3, datetime as d
c = sqlite3.connect("library.db")
c.execute("UPDATE loans SET due_date = ? WHERE id = 2", ((d.date.today() - d.timedelta(days=3)).isoformat(),))
c.commit()
exit()
```

Start the server again with `uvicorn main:app --reload`.

**37. GET /loans?status=overdue**

Expect: only loan 2, with `"due_date"` three days before TODAY, `"returned_date": null`, `"fine": 0` and `"is_overdue": true`.

**38. POST /loans/2/return**

Expect: `{"id": 2, "student_id": "2026-0001", "student_name": "Ana M. Cruz", "book_id": 2, "book_title": "The Pragmatic Programmer", "borrowed_date": "TODAY", "due_date": "TODAY-3", "returned_date": "TODAY", "fine": 15, "is_overdue": false}`

The fine is 3 days late times 5 pesos. `GET /books/2` now shows `"available_copies": 1`.