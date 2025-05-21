from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from SERVER.datebase import create_connection
from SERVER.models import Product, User, Documents, ClientProduct

app = FastAPI()

security = HTTPBasic()

# Функция для проверки пользователя
def verify_user(login: str, password: str):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE login = ? AND password = ?", (login, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            "id": user[0],
            "role": user[1],
            "login": user[2],
            "fio": user[4],
            "phone": user[5],
            "email": user[6],
            "passport": user[7],
            "adress": user[8]
        }
    return None


# Эндпоинт для авторизации и получения данных пользователя
@app.post("/auth")
async def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    user = verify_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


# Эндпоинт для изменения пароля
@app.post("/change-password")
async def change_password(
        request: Request,
        credentials: HTTPBasicCredentials = Depends(security)
):
    # Получаем новый пароль из тела запроса
    data = await request.json()
    new_password = data.get("new_password")

    if not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password is required"
        )

    # Проверяем текущие учетные данные
    current_user = verify_user(credentials.username, credentials.password)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current login or password"
        )

    # Обновляем пароль в базе данных
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE users SET password = ? WHERE login = ?",
            (new_password, credentials.username)
        )
        conn.commit()
        return {"message": "Password changed successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        conn.close()


# Получение всех пользователей с ролью "client"
@app.get("/users/clients")
async def get_clients():
    conn = create_connection()
    cursor = conn.cursor()

    # 1. Получаем всех клиентов
    cursor.execute("SELECT * FROM users WHERE role = 'client'")
    clients = cursor.fetchall()
    clients = list(clients)

    for i, client in enumerate(clients):
        client_id = client[0]

        # 2. Получаем продукты клиента
        cursor.execute("""
            SELECT products.name 
            FROM client_products 
            JOIN products ON products.id = client_products.product_id 
            WHERE client_id = ?
        """, (client_id,))
        products = [row[0] for row in cursor.fetchall()]

        # 3. Получаем дополнительные данные клиента из client_data
        cursor.execute("SELECT * FROM client_data WHERE client_id = ?", (client_id,))
        data_row = cursor.fetchone()

        # Преобразуем client в список
        client_list = list(client)

        # Добавляем продукты и доп. данные
        client_list.append(products)
        client_list.append(dict(data_row) if data_row else {})  # если есть, конвертируем Row в dict

        # Обновляем клиентский объект
        clients[i] = client_list

    conn.close()

    # Формируем финальный JSON-ответ
    return [{
        "id": client[0],
        "role": client[1],
        "login": client[2],
        "fio": client[4],
        "phone": client[5],
        "email": client[6],
        "passport": client[7],
        "adress": client[8],
        "products": client[9],             # список названий продуктов
        "client_data": client[10],         # словарь с данными из client_data
    } for client in clients]


# Обновленные эндпоинты (без авторизации)
@app.get("/products")
async def get_all_products():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM products")
    products = cursor.fetchall()
    conn.close()
    return [{"id": p[0], "name": p[1], "description": p[2]} for p in products]

@app.put("/products/{product_id}")
async def update_product(product_id: int, product: Product):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE products SET name = ?, description = ? WHERE id = ?",
            (product.name, product.description, product_id)
        )
        conn.commit()
        return {"message": "Product updated successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# Эндпоинт: Создать или обновить отчет
@app.post("/create_report/{client_id}")
async def create_report(client_id: int):
    conn = create_connection()
    cursor = conn.cursor()

    # Получаем данные из client_data
    cursor.execute("SELECT Income, Expenses FROM client_data WHERE client_id = ?", (client_id,))
    client_data = cursor.fetchone()

    if not client_data:
        raise HTTPException(status_code=404, detail="Client data not found")

    income = client_data["Income"]
    expenses = client_data["Expenses"]

    # Обновляем или создаем отчет
    cursor.execute("""
        INSERT OR REPLACE INTO reports (client_id, income, expenses)
        VALUES (?, ?, ?)
    """, (client_id, income, expenses))

    # Получаем продукты
    cursor.execute("""
        SELECT p.id, p.name, p.description 
        FROM client_products cp
        JOIN products p ON cp.product_id = p.id
        WHERE cp.client_id = ?
    """, (client_id,))
    products = [dict(row) for row in cursor.fetchall()]

    conn.commit()

    # Возвращаем созданный/обновленный отчет
    cursor.execute("SELECT * FROM reports WHERE client_id = ?", (client_id,))
    report = dict(cursor.fetchone())
    report['products'] = products
    conn.close()

    return report

@app.post("/create_user")
async def create_report(user: User):
    conn = create_connection()
    cursor = conn.cursor()
    print(user)

    # Обновляем или создаем отчет
    cursor.execute("""
        INSERT OR REPLACE INTO users (fio, email, phone, role, passport, login, password)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user.fio, user.email, user.phone, user.role, user.passport, user.login, user.password))
    client_id = cursor.lastrowid
    conn.commit()

    cursor.execute("""
        INSERT OR REPLACE INTO client_data (client_id, Income, Expenses, proposed_product)
        VALUES (?, ?, ?, "Дебетовая карта")
    """, (client_id, 0, 0))
    conn.commit()

@app.post("/create_doc")
async def create_report(doc: Documents):
    conn = create_connection()
    cursor = conn.cursor()
    # Обновляем или создаем отчет
    cursor.execute("""
        INSERT OR REPLACE INTO documents (report_id, client_id, is_signed)
        VALUES (?, ?, ?)
    """, (doc.report_id, doc.client_id, doc.is_signed))
    conn.commit()

@app.post("/add_client_product")
async def add_client_product(client: ClientProduct):
    conn = create_connection()
    cursor = conn.cursor()
    # Обновляем или создаем отчет
    cursor.execute("""
        INSERT OR REPLACE INTO client_products (client_id, product_id)
        VALUES (?, ?)
    """, (client.client_id, client.product_id))
    conn.commit()


@app.post("/del_client_product")
async def del_client_product(client: ClientProduct):
    conn = create_connection()
    cursor = conn.cursor()
    # Обновляем или создаем отчет
    cursor.execute("""
        DELETE FROM client_products WHERE client_id = ? AND product_id = ?
    """, (client.client_id, client.product_id))
    conn.commit()


# Эндпоинт: Получить отчет по client_id
@app.get("/get_report/{client_id}")
async def get_report(client_id: int):
    conn = create_connection()
    cursor = conn.cursor()

    # Получаем данные клиента
    cursor.execute("SELECT id, fio FROM users WHERE id = ?", (client_id,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM documents WHERE client_id = ?", (client_id,))
    documents = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем данные из client_data
    cursor.execute("SELECT id, Income, Expenses FROM reports WHERE client_id = ?", (client_id,))
    client_data = cursor.fetchone()

    if not client_data:
        raise HTTPException(status_code=404, detail="Client data not found")

    # Получаем список продуктов клиента
    cursor.execute("""
        SELECT p.id, p.name, p.description 
        FROM client_products cp
        JOIN products p ON cp.product_id = p.id
        WHERE cp.client_id = ?
    """, (client_id,))
    products = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "id": client_data["id"],
        "client_id": user["id"],
        "fio": user["fio"],
        "income": client_data["Income"],
        "expenses": client_data["Expenses"],
        "products": products,
        "doc": documents
    }

@app.get("/get_all_reports")
async def get_all_reports():
    conn = create_connection()
    cursor = conn.cursor()

    # Получаем всех клиентов, у которых есть запись в client_data
    cursor.execute("""
        SELECT u.id AS client_id, u.fio
        FROM users u
        JOIN client_data cd ON u.id = cd.client_id
    """)
    users = cursor.fetchall()

    if not users:
        raise HTTPException(status_code=404, detail="No clients found with data")

    reports = []

    for user in users:
        client_id = user["client_id"]

        cursor.execute("SELECT id FROM reports WHERE client_id = ?", (client_id,))
        report = cursor.fetchone()
        if not report:
            continue

        # Получаем доходы и расходы
        cursor.execute("SELECT Income, Expenses FROM client_data WHERE client_id = ?", (client_id,))
        client_data = cursor.fetchone()

        # Получаем продукты
        cursor.execute("""
            SELECT p.id, p.name, p.description 
            FROM client_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.client_id = ?
        """, (client_id,))
        products = [dict(row) for row in cursor.fetchall()]

        reports.append({
            "client_id": user["client_id"],
            "fio": user["fio"],
            "income": client_data["Income"],
            "expenses": client_data["Expenses"],
            "products": products
        })

    conn.close()

    return reports

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)