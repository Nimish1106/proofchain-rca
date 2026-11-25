from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient


def create_sample_investigation(client: TestClient) -> dict:
    """Create a reusable investigation for tests."""
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "API contamination investigation",
            "product_name": "Metformin Hydrochloride API",
            "product_grade": "IP",
            "batch_number": "MTF26001",
            "manufacturing_site": "Site A",
            "process_stage": "Filtration",
            "incident_date": "2026-11-20",
            "affected_quantity": "25.500",
            "affected_unit": "kg",
            "incident_description": (
                "Foreign matter detected in one API drum."
            ),
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_investigation(client: TestClient):
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "API contamination investigation",
            "product_name": "Metformin Hydrochloride API",
            "batch_number": "MTF26001",
            "affected_quantity": "25.500",
            "affected_unit": "kg",
        },
    )
    assert response.status_code == 201
    data = response.json()
    UUID(data["id"])
    assert data["title"] == "API contamination investigation"
    assert data["status"] == "draft"
    assert data["product_name"] == "Metformin Hydrochloride API"
    assert Decimal(data["affected_quantity"]) == Decimal("25.500")
    assert data["affected_unit"] == "kg"
    assert "created_at" in data
    assert "updated_at" in data


def test_create_investigation_normalizes_text(client: TestClient):
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "  Equipment investigation  ",
            "product_name": "  Metformin API  ",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Equipment investigation"
    assert data["product_name"] == "Metformin API"


def test_get_investigation(client: TestClient):
    created = create_sample_investigation(client)
    response = client.get(
        f"/api/v1/investigations/{created['id']}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["batch_number"] == "MTF26001"


def test_list_investigations(client: TestClient):
    create_sample_investigation(client)
    second_response = client.post(
        "/api/v1/investigations",
        json={
            "title": "Filtration deviation investigation",
        },
    )
    assert second_response.status_code == 201

    response = client.get(
        "/api/v1/investigations?limit=10&offset=0"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_update_preserves_unmodified_fields(
    client: TestClient,
):
    created = create_sample_investigation(client)
    response = client.patch(
        f"/api/v1/investigations/{created['id']}",
        json={
            "affected_quantity": "50",
            "affected_unit": "kg",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["affected_quantity"]) == Decimal("50")
    assert data["affected_unit"] == "kg"
    # These fields must remain unchanged.
    assert data["title"] == "API contamination investigation"
    assert data["batch_number"] == "MTF26001"
    assert data["product_name"] == "Metformin Hydrochloride API"


def test_update_can_clear_optional_fields(
    client: TestClient,
):
    created = create_sample_investigation(client)
    response = client.patch(
        f"/api/v1/investigations/{created['id']}",
        json={
            "batch_number": None,
            "affected_quantity": None,
            "affected_unit": None,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch_number"] is None
    assert data["affected_quantity"] is None
    assert data["affected_unit"] is None
    assert data["product_name"] == "Metformin Hydrochloride API"


def test_empty_update_is_rejected(client: TestClient):
    created = create_sample_investigation(client)
    response = client.patch(
        f"/api/v1/investigations/{created['id']}",
        json={},
    )
    assert response.status_code == 422


def test_invalid_quantity_is_rejected(client: TestClient):
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "Invalid quantity investigation",
            "affected_quantity": "0",
        },
    )
    assert response.status_code == 422


def test_unknown_fields_are_rejected(client: TestClient):
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "Invalid investigation",
            "unknown_field": "unexpected value",
        },
    )
    assert response.status_code == 422


def test_status_cannot_be_changed_through_general_update(
    client: TestClient,
):
    created = create_sample_investigation(client)
    response = client.patch(
        f"/api/v1/investigations/{created['id']}",
        json={
            "status": "completed",
        },
    )
    assert response.status_code == 422


def test_missing_investigation_returns_404(
    client: TestClient,
):
    missing_id = "00000000-0000-0000-0000-000000000001"
    response = client.get(
        f"/api/v1/investigations/{missing_id}"
    )
    assert response.status_code == 404


def test_invalid_uuid_returns_422(client: TestClient):
    response = client.get(
        "/api/v1/investigations/not-a-valid-uuid"
    )
    assert response.status_code == 422


def test_invalid_pagination_is_rejected(client: TestClient):
    response = client.get(
        "/api/v1/investigations?limit=500"
    )
    assert response.status_code == 422
