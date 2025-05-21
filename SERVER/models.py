# models.py
from pydantic import BaseModel

class User(BaseModel):
    id: int | None = None
    role: str
    login: str
    password: str
    fio: str | None = None
    phone: str | None = None
    email: str | None = None
    passport: str | None = None
    adress: str | None = None

class UserLogin(BaseModel):
    login: str
    password: str

class Product(BaseModel):
    id: int | None = None
    name: str
    description: str

class Documents(BaseModel):
    report_id: int
    client_id: int
    is_signed: bool = False

class ClientProduct(BaseModel):
    client_id: int
    product_id: int
