from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

from fastapi.testclient import TestClient


sys.path.append(str(Path(__file__).resolve().parent.parent))

import api
from api import app, get_current_user
from codex.neo4j_driver import get_bulk_translation_records


client = TestClient(app)


def _authenticated_as(role="administrator"):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "exporter@example.com",
        "role": role,
    }


def _mock_driver():
    mock_driver = MagicMock()
    mock_session = mock_driver.session.return_value.__enter__.return_value
    return mock_driver, mock_session


def teardown_function():
    app.dependency_overrides.clear()


def test_bulk_return_requires_authentication():
    response = client.get("/api/bulk-return")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_bulk_return_rejects_unpermitted_role():
    _authenticated_as("viewer")

    response = client.get("/api/bulk-return")

    assert response.status_code == 403


def test_bulk_return_filters_fields_and_range():
    _authenticated_as()
    mock_driver, mock_session = _mock_driver()
    records = [
        {
            "canonical": "ibuprofen",
            "translation": "ibuprofeno",
            "brand": "Advil",
        },
    ]

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(
            api,
            "get_bulk_translation_records",
            return_value=(8, ["canonical", "translation", "brand"], records),
        ) as mock_get_bulk,
    ):
        response = client.get(
            "/api/bulk-return?start=2&end=5&fields=canonical,brand"
        )

    assert response.status_code == 200
    assert response.json() == {
        "range": {"start": 2, "end": 2},
        "total": 8,
        "count": 1,
        "columns": ["canonical", "brand"],
        "rows": [
            {"canonical": "ibuprofen", "brand": "Advil"},
        ],
    }
    mock_get_bulk.assert_called_once_with(
        mock_session,
        start=2,
        end=5,
    )


def test_bulk_return_defaults_to_joined_translation_rows():
    _authenticated_as("medical professional")
    mock_driver, _ = _mock_driver()
    fields = [
        "canonical",
        "term_type",
        "translation",
        "brand",
        "country_code",
        "country_name",
        "language_code",
        "language_name",
    ]
    record = {
        "canonical": "ibuprofen",
        "term_type": "medication",
        "translation": "ibuprofeno",
        "brand": "Advil",
        "country_code": "MX",
        "country_name": "Mexico",
        "language_code": "es",
        "language_name": "Spanish",
    }

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(
            api,
            "get_bulk_translation_records",
            return_value=(1, fields, [record]),
        ),
    ):
        response = client.get("/api/bulk-return")

    assert response.status_code == 200
    assert response.json()["columns"] == fields
    assert response.json()["rows"] == [record]


def test_bulk_return_validates_range_and_requested_fields():
    _authenticated_as()
    mock_driver, _ = _mock_driver()

    invalid_range = client.get("/api/bulk-return?start=4&end=3")
    assert invalid_range.status_code == 422

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(
            api,
            "get_bulk_translation_records",
            return_value=(1, ["canonical"], [{"canonical": "ibuprofen"}]),
        ),
    ):
        unknown_field = client.get("/api/bulk-return?fields=not_a_field")

    assert unknown_field.status_code == 422
    assert unknown_field.json()["detail"]["unknown_fields"] == ["not_a_field"]


def test_get_bulk_translation_records_returns_joined_rows():
    session = MagicMock()
    count_result = MagicMock()
    count_result.single.return_value = {"total": 1}
    row = {
        "canonical": "ibuprofen",
        "term_type": "medication",
        "translation": "ibuprofeno",
        "brand": "Advil",
        "country_code": "MX",
        "country_name": "Mexico",
        "language_code": "es",
        "language_name": "Spanish",
    }
    session.run.side_effect = [count_result, [row]]

    total, fields, rows = get_bulk_translation_records(session, start=0, end=9)

    assert total == 1
    assert fields == list(row)
    assert rows == [row]
    assert session.run.call_args_list[1].kwargs["limit"] == 10
