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

If `uvicorn` is not recognized, use:

```powershell
python -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to try every endpoint (click an endpoint, then Try it out). The database file `library.db` is created in the project folder on first start. To start from an empty database, stop the server and delete `library.db`.

## Project tree

```text
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

Run them in order on an empty database, using the /docs page. Each step shows the request, the body to send (JSON), and the output to expect (JSON).

- TODAY means today's date in YYYY-MM-DD form. TODAY+7 means seven days later, TODAY-3 means three days earlier.
- Business-rule errors come back as `{"detail": "<message>"}`.
- Input mistakes come back as `{"detail": [ ... ]}` with a `loc` naming the bad field.

### Root

**1. Welcome message**

```http
GET /
```

Expect:

```json
{
  "message": "Welcome to the Library Book Borrowing System API"
}
```

### Books

**2. Add a book**

```http
POST /books
```

Body:

```json
{
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "total_copies": 2
}
```

Expect:

```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "total_copies": 2,
  "available_copies": 2
}
```

**3. Add three more books**

```http
POST /books
```

Send each body one at a time. They return ids 2, 3 and 4, with `available_copies` equal to `total_copies`.

```json
{
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "isbn": "9780135957059",
  "total_copies": 1
}
```

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "isbn": "9780441013593",
  "total_copies": 1
}
```

```json
{
  "title": "Refactoring",
  "author": "Martin Fowler",
  "isbn": "9780134757599",
  "total_copies": 1
}
```

**4. Duplicate ISBN**

```http
POST /books
```

Body (same ISBN as step 2):

```json
{
  "title": "Clean Code Copy",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "total_copies": 1
}
```

Expect:

```json
{
  "detail": "A book with ISBN '9780132350884' already exists"
}
```

**5. Invalid input**

```http
POST /books
```

Body:

```json
{
  "title": "X",
  "author": "Y",
  "isbn": "9780000000002",
  "total_copies": 0
}
```

Expect (the exact wording can differ slightly between Pydantic versions):

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "total_copies"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0,
      "ctx": { "ge": 1 }
    }
  ]
}
```

An unknown extra field, an empty title, or an ISBN like `abc` gives the same kind of error.

**6. List all books**

```http
GET /books
```

Expect: a list of the 4 books, each with `available_copies` equal to `total_copies`.

**7. Search by title or author**

```http
GET /books?q=clean
```

Expect:

```json
[
  {
    "id": 1,
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "9780132350884",
    "total_copies": 2,
    "available_copies": 2
  }
]
```

`GET /books?q=herbert` returns only Dune (author search).

**8. Only available books**

```http
GET /books?available_only=true
```

Expect: all 4 books for now. Repeat it after step 29.

**9. Get one book**

```http
GET /books/1
```

Expect: the Clean Code record from step 2.

```http
GET /books/99
```

Expect:

```json
{
  "detail": "Book '99' not found"
}
```

**10. Update a book**

```http
PUT /books/1
```

Body:

```json
{
  "title": "Clean Code, 2nd Printing"
}
```

Expect:

```json
{
  "id": 1,
  "title": "Clean Code, 2nd Printing",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "total_copies": 2,
  "available_copies": 2
}
```

A body of `{}` gives an input error (at least one field is required).

### Students

**11. Register a student**

```http
POST /students
```

Body:

```json
{
  "student_id": "2026-0001",
  "name": "Ana Cruz",
  "email": "ana.cruz@um.edu.ph"
}
```

Expect:

```json
{
  "student_id": "2026-0001",
  "name": "Ana Cruz",
  "email": "ana.cruz@um.edu.ph"
}
```

**12. Register two more students**

```http
POST /students
```

Send each body one at a time. Each returns the student.

```json
{
  "student_id": "2026-0002",
  "name": "Ben Reyes",
  "email": "ben.reyes@um.edu.ph"
}
```

```json
{
  "student_id": "2026-0003",
  "name": "Cara Lim",
  "email": "cara.lim@um.edu.ph"
}
```

**13. Duplicates and bad input**

```http
POST /students
```

Duplicate email, body:

```json
{
  "student_id": "2026-0009",
  "name": "Dup",
  "email": "ana.cruz@um.edu.ph"
}
```

Expect:

```json
{
  "detail": "Email 'ana.cruz@um.edu.ph' is already registered"
}
```

Duplicate student ID, body:

```json
{
  "student_id": "2026-0001",
  "name": "Dup",
  "email": "dup@um.edu.ph"
}
```

Expect:

```json
{
  "detail": "Student ID '2026-0001' already exists"
}
```

An email like `not-an-email` gives an input error naming `email`.

**14. Search students**

```http
GET /students?q=cruz
```

Expect:

```json
[
  {
    "student_id": "2026-0001",
    "name": "Ana Cruz",
    "email": "ana.cruz@um.edu.ph"
  }
]
```

`GET /students?q=0002` returns Ben (search by student ID). `GET /students` returns all 3.

**15. Get one student**

```http
GET /students/2026-0001
```

Expect: Ana's record.

```http
GET /students/nope
```

Expect:

```json
{
  "detail": "Student 'nope' not found"
}
```

**16. Update a student**

```http
PUT /students/2026-0001
```

Body:

```json
{
  "name": "Ana M. Cruz"
}
```

Expect:

```json
{
  "student_id": "2026-0001",
  "name": "Ana M. Cruz",
  "email": "ana.cruz@um.edu.ph"
}
```

A body of `{"student_id": "x"}` gives an input error (student ID cannot change). Body:

```json
{
  "email": "ben.reyes@um.edu.ph"
}
```

Expect:

```json
{
  "detail": "Email 'ben.reyes@um.edu.ph' is already registered"
}
```

**17. Delete a student with no loans**

```http
DELETE /students/2026-0003
```

Expect: an empty response (deleted). Repeating it expects:

```json
{
  "detail": "Student '2026-0003' not found"
}
```

### Borrowing

**18. Borrow a book**

```http
POST /loans
```

Body:

```json
{
  "student_id": "2026-0001",
  "book_id": 1,
  "days": 7
}
```

Expect:

```json
{
  "id": 1,
  "student_id": "2026-0001",
  "student_name": "Ana M. Cruz",
  "book_id": 1,
  "book_title": "Clean Code, 2nd Printing",
  "borrowed_date": "TODAY",
  "due_date": "TODAY+7",
  "returned_date": null,
  "fine": 0,
  "is_overdue": false
}
```

`GET /books/1` now shows `"available_copies": 1`.

**19. Two more loans for Ana**

```http
POST /loans
```

Send each body one at a time. They return loans 2 and 3. Ana now has 3 active loans.

```json
{
  "student_id": "2026-0001",
  "book_id": 2,
  "days": 7
}
```

```json
{
  "student_id": "2026-0001",
  "book_id": 3,
  "days": 7
}
```

**20. The 3-active-loans limit**

```http
POST /loans
```

Body:

```json
{
  "student_id": "2026-0001",
  "book_id": 4,
  "days": 7
}
```

Expect:

```json
{
  "detail": "Student already has 3 active loans"
}
```

**21. Rollback check**

```http
GET /books/4
```

Expect `"available_copies": 1` (unchanged).

```http
GET /loans
```

Expect only 3 loans. The failed borrow saved nothing.

**22. Same book twice**

```http
POST /loans
```

Body:

```json
{
  "student_id": "2026-0001",
  "book_id": 1,
  "days": 7
}
```

Expect:

```json
{
  "detail": "Student already has this book on loan"
}
```

**23. No copies left**

```http
POST /loans
```

Body:

```json
{
  "student_id": "2026-0002",
  "book_id": 2,
  "days": 7
}
```

Expect:

```json
{
  "detail": "No copies of 'The Pragmatic Programmer' are available"
}
```

**24. Unknown student, unknown book, bad days**

```http
POST /loans
```

Unknown student, body:

```json
{
  "student_id": "nope",
  "book_id": 1,
  "days": 7
}
```

Expect:

```json
{
  "detail": "Student 'nope' not found"
}
```

Unknown book, body:

```json
{
  "student_id": "2026-0002",
  "book_id": 999,
  "days": 7
}
```

Expect:

```json
{
  "detail": "Book '999' not found"
}
```

`"days": 0` or `"days": 31` gives an input error naming `days`.

**25. Ben borrows the second copy of book 1**

```http
POST /loans
```

Body:

```json
{
  "student_id": "2026-0002",
  "book_id": 1,
  "days": 7
}
```

Expect: loan 4 for Ben. `GET /books/1` now shows `"available_copies": 0`.

### Books again (rules with loans)

**26. Total copies below copies on loan**

```http
PUT /books/1
```

Body:

```json
{
  "total_copies": 1
}
```

Expect:

```json
{
  "detail": "Total copies cannot be below the 2 copies currently on loan"
}
```

**27. Raise total copies**

```http
PUT /books/1
```

Body:

```json
{
  "total_copies": 5
}
```

Expect:

```json
{
  "id": 1,
  "title": "Clean Code, 2nd Printing",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "total_copies": 5,
  "available_copies": 3
}
```

**28. Delete protection**

```http
DELETE /books/1
```

Expect:

```json
{
  "detail": "Book has loan records and cannot be deleted"
}
```

```http
DELETE /students/2026-0001
```

Expect:

```json
{
  "detail": "Student has loan records and cannot be deleted"
}
```

**29. Only available books again**

```http
GET /books?available_only=true
```

Expect: only book 1 (`"available_copies": 3`) and book 4 (`"available_copies": 1`).

### Loan lookups

**30. List loans and filter by status**

```http
GET /loans
```

Expect: loans 1 to 4.

```http
GET /loans?status=active
```

Expect: loans 1 to 4.

```http
GET /loans?status=returned
```

Expect:

```json
[]
```

```http
GET /loans?status=overdue
```

Expect:

```json
[]
```

`GET /loans?status=bogus` gives an input error naming `status`.

**31. Get one loan**

```http
GET /loans/1
```

Expect: the loan from step 18, showing `"book_title": "Clean Code, 2nd Printing"` and `"student_name": "Ana M. Cruz"`.

```http
GET /loans/999
```

Expect:

```json
{
  "detail": "Loan '999' not found"
}
```

**32. All loans of a student**

```http
GET /students/2026-0001/loans
```

Expect: 3 loans (ids 1, 2, 3) whose `book_title` values are "Clean Code, 2nd Printing", "The Pragmatic Programmer", and "Dune".

```http
GET /students/nope/loans
```

Expect:

```json
{
  "detail": "Student 'nope' not found"
}
```

### Returning

**33. Return a book on time**

```http
POST /loans/1/return
```

Expect:

```json
{
  "id": 1,
  "student_id": "2026-0001",
  "student_name": "Ana M. Cruz",
  "book_id": 1,
  "book_title": "Clean Code, 2nd Printing",
  "borrowed_date": "TODAY",
  "due_date": "TODAY+7",
  "returned_date": "TODAY",
  "fine": 0,
  "is_overdue": false
}
```

`GET /books/1` now shows `"available_copies": 4`.

**34. Return errors**

```http
POST /loans/1/return
```

Expect:

```json
{
  "detail": "Loan has already been returned"
}
```

```http
POST /loans/999/return
```

Expect:

```json
{
  "detail": "Loan '999' not found"
}
```

**35. Status filters after a return**

```http
GET /loans?status=returned
```

Expect: only loan 1.

```http
GET /loans?status=active
```

Expect: loans 2, 3 and 4.

### Late return with a fine

**36. Backdate loan 2 by 3 days**

There is no endpoint for this, so change the date in the database. Stop the server first (Ctrl+C), then in the project folder start Python:

```powershell
python
```

Type these lines one at a time:

```python
import sqlite3, datetime as d
c = sqlite3.connect("library.db")
c.execute("UPDATE loans SET due_date = ? WHERE id = 2", ((d.date.today() - d.timedelta(days=3)).isoformat(),))
c.commit()
exit()
```

Start the server again:

```powershell
uvicorn main:app --reload
```

**37. See the overdue loan**

```http
GET /loans?status=overdue
```

Expect: only loan 2:

```json
[
  {
    "id": 2,
    "student_id": "2026-0001",
    "student_name": "Ana M. Cruz",
    "book_id": 2,
    "book_title": "The Pragmatic Programmer",
    "borrowed_date": "TODAY",
    "due_date": "TODAY-3",
    "returned_date": null,
    "fine": 0,
    "is_overdue": true
  }
]
```

**38. Return it late**

```http
POST /loans/2/return
```

Expect (3 days late times 5 pesos):

```json
{
  "id": 2,
  "student_id": "2026-0001",
  "student_name": "Ana M. Cruz",
  "book_id": 2,
  "book_title": "The Pragmatic Programmer",
  "borrowed_date": "TODAY",
  "due_date": "TODAY-3",
  "returned_date": "TODAY",
  "fine": 15,
  "is_overdue": false
}
```

`GET /books/2` now shows `"available_copies": 1`.