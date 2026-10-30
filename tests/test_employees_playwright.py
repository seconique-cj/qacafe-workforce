import threading
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import app
from database import conn, cursor


@pytest.fixture
def api_request():
    server = make_server("127.0.0.1", 0, app)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        with sync_playwright() as playwright:
            request_context = playwright.request.new_context(
                base_url=f"http://127.0.0.1:{server.server_port}"
            )
            try:
                yield request_context
            finally:
                request_context.dispose()
    finally:
        server.shutdown()
        server_thread.join()


@pytest.fixture
def employee_data():
    employee = {
        "name": f"Playwright Test {uuid4().hex}",
        "start_date": "2026-10-30",
        "location": "Test Location",
        "role": "Test Role",
    }

    yield employee

    cursor.execute("DELETE FROM employees WHERE name = ?", (employee["name"],))
    conn.commit()


def test_get_employees_returns_employee_list(api_request, employee_data):
    create_response = api_request.post("/employees", data=employee_data)
    assert create_response.status == 201

    response = api_request.get("/employees")

    assert response.status == 200
    employees = response.json()
    assert isinstance(employees, list)
    assert any(employee_data["name"] == employee[1] for employee in employees)


def test_post_employee_creates_employee(api_request, employee_data):
    response = api_request.post("/employees", data=employee_data)

    assert response.status == 201

    employees_response = api_request.get("/employees")
    assert employees_response.status == 200
    assert any(
        employee_data["name"] == employee[1]
        for employee in employees_response.json()
    )
