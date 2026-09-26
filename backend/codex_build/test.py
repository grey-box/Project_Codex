
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

import api




def test_create_user():
    mock_session = MagicMock()

    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    new_user = {
        "email": "jane.doe@example.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "affiliation": "Global Health Org",
        "created_at": "2026-09-26T15:00:00",
    }

    with patch.object(api, "driver", mock_driver), \
         patch.object(api, "get_user_by_email", return_value=None), \
         patch.object(api, "create_user", return_value=new_user):

        client = TestClient(api.app)

        response = client.post(
            "/users",
            json={
                "real_name": "Jane Doe",
                "password": "SecurePassword123!",
                "role": "Admin",
                "affiliation": "Global Health Org",
                "email": "jane.doe@example.com",
            },
        )

    assert response.status_code == 201
    assert response.json() == new_user
