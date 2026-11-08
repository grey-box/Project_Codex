from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

from fastapi.testclient import TestClient


sys.path.append(str(Path(__file__).resolve().parent.parent))

import api
from api import app, get_current_user
from codex.neo4j_driver import get_bulk_records


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


def test_bulk_return_filters_fields_labels_and_range():
    _authenticated_as()
    mock_driver, mock_session = _mock_driver()
    records = [
        {
            "_labels": ["DRUG"],
            "id": "DB0001",
            "title": "Example drug",
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        },
        {
            "_labels": ["RXN"],
            "id": "2",
            "title": None,
        },
    ]

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(
            api,
            "get_bulk_records",
            return_value=(8, ["created_at", "id", "title"], records),
        ) as mock_get_bulk,
    ):
        response = client.get(
            "/api/bulk-return?start=2&end=5&labels=DRUG,RXN&fields=id,title"
        )

    assert response.status_code == 200
    assert response.json() == {
        "range": {"start": 2, "end": 3},
        "total": 8,
        "count": 2,
        "columns": ["id", "title"],
        "rows": [
            {"id": "DB0001", "title": "Example drug"},
            {"id": "2", "title": None},
        ],
    }
    mock_get_bulk.assert_called_once_with(
        mock_session,
        start=2,
        end=5,
        node_labels=["DRUG", "RXN"],
    )


def test_bulk_return_includes_all_columns_and_json_safe_values_by_default():
    _authenticated_as("medical professional")
    mock_driver, _ = _mock_driver()
    created_at = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(
            api,
            "get_bulk_records",
            return_value=(1, ["created_at", "id"], [{
                "_labels": ["ICD"],
                "id": "abc",
                "created_at": created_at,
            }]),
        ),
    ):
        response = client.get("/api/bulk-return")

    assert response.status_code == 200
    assert response.json()["columns"] == ["_labels", "created_at", "id"]
    assert response.json()["rows"] == [{
        "_labels": ["ICD"],
        "created_at": created_at.isoformat(),
        "id": "abc",
    }]


def test_bulk_return_validates_range_and_requested_fields():
    _authenticated_as()
    mock_driver, _ = _mock_driver()

    invalid_range = client.get("/api/bulk-return?start=4&end=3")
    assert invalid_range.status_code == 422

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(
            api,
            "get_bulk_records",
            return_value=(1, ["id"], [{"_labels": ["DRUG"], "id": "1"}]),
        ),
    ):
        unknown_field = client.get("/api/bulk-return?fields=not_a_field")

    assert unknown_field.status_code == 422
    assert unknown_field.json()["detail"]["unknown_fields"] == ["not_a_field"]


def test_get_bulk_records_excludes_users_and_uses_inclusive_end():
    session = MagicMock()
    count_result = MagicMock()
    count_result.single.return_value = {"total": 2}
    field_result = [{"field": "id"}, {"field": "title"}]
    row_result = [
        {"labels": ["DRUG"], "attributes": {"id": "1", "title": "One"}},
        {"labels": ["DRUG"], "attributes": {"id": "2", "title": "Two"}},
    ]
    session.run.side_effect = [count_result, field_result, row_result]

    total, fields, rows = get_bulk_records(
        session,
        start=3,
        end=4,
        node_labels=["DRUG"],
    )

    assert total == 2
    assert fields == ["id", "title"]
    assert rows == [
        {"id": "1", "title": "One", "_labels": ["DRUG"]},
        {"id": "2", "title": "Two", "_labels": ["DRUG"]},
    ]
    assert session.run.call_count == 3

    for call in session.run.call_args_list:
        assert "NOT n:User" in call.args[0]
        assert call.kwargs["node_labels"] == ["DRUG"]

    data_call = session.run.call_args_list[2]
    assert "LIMIT $limit" in data_call.args[0]
    assert data_call.kwargs["start"] == 3
    assert data_call.kwargs["limit"] == 2
