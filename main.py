from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import database
from app.exceptions import BusinessRuleError, NotFoundError
from app.routers import books, loans, students


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.create_schema()
    yield


app = FastAPI(title="Library Book Borrowing System", version="casper", lifespan=lifespan)

app.include_router(books.router)
app.include_router(students.router)
app.include_router(loans.router)


@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def handle_business_rule(request: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/")
def read_root():
    return {"message": "Welcome to the Library Book Borrowing System API"}