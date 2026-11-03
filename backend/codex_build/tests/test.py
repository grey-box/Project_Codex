from unittest.mock import MagicMock, patch


from pathlib import Path
import sys
from fastapi.testclient import TestClient
# Get the path of the current file's parent's parent (the parent directory)
parent_dir = str(Path(__file__).resolve().parent.parent)

# Add it to the module search path
sys.path.append(parent_dir)

from api import app
import api




client = TestClient(app)


def create_mock_driver():
    """Create a mock Neo4j driver and session."""
    mock_session = MagicMock()
    mock_driver = MagicMock()

    mock_driver.session.return_value.__enter__.return_value = mock_session

    return mock_driver, mock_session


#__GET USERS TEST CASES__________________________________________________

def test_get_users():
    mock_users = [
        {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
        {
            "email": "john@email.com",
            "real_name": "John Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
    ]

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_all_users", return_value=mock_users) as mock_get_all,
    ):
        response = client.get("/users")

    assert response.status_code == 200
    assert response.json() == mock_users

    mock_get_all.assert_called_once_with(
        mock_session,
        limit=100,
    )
    
def test_driver_get_all_users():
    mock_users = [
        {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
        {
            "email": "john@email.com",
            "real_name": "John Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
    ]
    record1 = MagicMock()
    record1.data.return_value = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "affiliation": "grey-box",
        "created_at": None
    }
    record2 = MagicMock()
    record2.data.return_value = {
        "email": "john@email.com",
        "real_name": "John Doe",
        "role": "Admin",
        "affiliation": "grey-box",
        "created_at": None
    }
    mock_result = [record1, record2]
    mock_session = MagicMock()
    mock_session.run.return_value = mock_result

    
    result = api.get_all_users(mock_session, 100)
    assert result == mock_users
    mock_session.run.assert_called_once()
     

def test_get_users_with_limit():
    mock_users = [
        {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
        {
            "email": "john@email.com",
            "real_name": "John Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
    ]

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_all_users", return_value=mock_users) as mock_get_all,
        ):
        response = client.get("/users?limit=10")

    assert response.status_code == 200

    mock_get_all.assert_called_once_with(
        mock_session,
        limit=10,
    )


def test_get_users_by_role():
    mock_users = [
        {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
        {
            "email": "john@email.com",
            "real_name": "John Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        },
    ]

    mock_driver, mock_session = create_mock_driver()

    with (
            patch.object(api, "driver", mock_driver),
            patch.object(api, "get_users_by_role", return_value=mock_users) as mock_get_by_role,
        ):
        response = client.get("/users?role=admin")

    assert response.status_code == 200
    assert response.json() == mock_users

    mock_get_by_role.assert_called_once_with(
        mock_session,
        "admin",
    )


def test_get_users_invalid_limit_too_small():
    response = client.get("/users?limit=0")

    assert response.status_code == 422


def test_get_users_invalid_limit_too_large():
    response = client.get("/users?limit=1001")

    assert response.status_code == 422


def test_get_users_invalid_limit():
    response = client.get("/users?limit=abc")

    assert response.status_code == 422


def test_get_users_database_error():
    mock_driver, mock_session = create_mock_driver()

    with (
            patch.object(api, "driver", mock_driver),
            patch.object(api, "get_all_users", side_effect=Exception("Database connection failed")),
        ):
        response = client.get("/users")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Database connection failed"
    }
    
def test_get_user_by_email():
    mock_users = {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        }

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=mock_users) as mock_get_user,
    ):
        response = client.get(f"/users/{mock_users["email"]}")

    assert response.status_code == 200
    assert response.json() == mock_users

    mock_get_user.assert_called_once_with(
        mock_session,
        mock_users["email"]
    )
    
def test_get_invalid_user_by_email():
    mock_users = {
            "email": "jane@email.com",
            "real_name": "Jane Doe",
            "role": "Admin",
            "affiliation": "grey-box",
            "created_at": None
        }

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=None) as mock_get_user,
    ):
        response = client.get(f"/users/abc")

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"User 'abc' not found."
    }

    mock_get_user.assert_called_once_with(
        mock_session,
        "abc"
    )
    
#__CREATE USERS TEST CASES__________________________________________________

def test_create_user():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=None),
        patch.object(api, "create_user", return_value=mock_users) as mock_create_user,
    ):
        response = client.post(
            "/users",
            json=mock_users
        )

    assert response.status_code == 201
    assert response.json()["email"] == mock_users["email"]
    
    mock_create_user.assert_called_once_with(
        mock_session,
        real_name=mock_users["real_name"],
        password=mock_users["password"],
        role=mock_users["role"],
        affiliation=mock_users["affiliation"],
        email=mock_users["email"]
    )

def test_create_user_already_exists():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=None),
        patch.object(api, "create_user", return_value=mock_users),
    ):
        client.post(
            "/users",
            json=mock_users
        )
        
    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=any) as mock_get_user_by_email,
    ):   
        response = client.post(
            "/users",
            json=mock_users
        )

    assert response.status_code == 409
    assert response.json()["detail"] == f"User with email '{mock_users["email"]}' already exists."
    
    mock_get_user_by_email.assert_called_with(
        mock_session,
        mock_users["email"]
    )
    
def test_create_user_invalid_user():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=None),
        patch.object(api, "create_user", return_value=None) as mock_create_user,
    ):
        response = client.post(
            "/users",
            json=mock_users
        )

    assert response.status_code == 500
    assert response.json()["detail"] == f"Failed to create user node."
    
    mock_create_user.assert_called_once_with(
            mock_session,
            real_name=mock_users["real_name"],
            password=mock_users["password"],
            role=mock_users["role"],
            affiliation=mock_users["affiliation"],
            email=mock_users["email"]
    )
    
#__UPDATE USERS TEST CASES__________________________________________________

def test_update_user():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }
    
    updated_user = {
        "email": "jane@email.com",
        "real_name": "Janice Doe",
        "role": "User",
        "password": "password123",
        "affiliation": "some company",
        "created_at": None
    }

    mock_driver, mock_session = create_mock_driver()

    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "update_user", return_value=updated_user) as mock_update_user,
    ):
        
        response = client.patch(
            f"/users/{mock_users["email"]}",
            json=updated_user
        )

    assert response.status_code == 200
    assert response.json()["email"] == updated_user["email"]
    assert response.json()["real_name"] == updated_user["real_name"]
    assert response.json()["role"] == updated_user["role"]
    assert response.json()["affiliation"] == updated_user["affiliation"]
    
    mock_update_user.assert_called_with(
        mock_session,
        email=updated_user["email"],
        real_name=updated_user["real_name"],
        role=updated_user["role"],
        affiliation=updated_user["affiliation"],
        password=updated_user["password"]
    )
    
def test_update_user_no_changes():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }
    
    updated_user = {
            "email": "jane@email.com",
            "real_name": None,
            "role": None,
            "password": None,
            "affiliation": None,
            "created_at": None
        }
    
    mock_driver, mock_session = create_mock_driver()
    
    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "get_user_by_email", return_value=None),
        patch.object(api, "create_user", return_value=mock_users),
    ):
        response = client.post(
            "/users",
            json=mock_users
        )
    
    assert response.status_code == 201

    with (
        patch.object(api, "driver", mock_driver),
        #patch.object(mock_session, "run", return_value=None)
        #patch.object(api, "update_user", return_value=None) as mock_update_user,
    ):
        
        response = client.patch(
            f"/users/{mock_users["email"]}",
            json=updated_user
        )

    assert response.status_code == 404
    assert response.json()["detail"] == f"User '{mock_users["email"]}' not found or no changes were made."
    
    # mock_update_user.assert_called_with(
    #     mock_session,
    #     email=mock_users["email"],
    #     real_name=mock_users["real_name"],
    #     role=mock_users["role"],
    #     affiliation=mock_users["affiliation"],
    #     password=mock_users["password"]
    # )

def test_delete_user():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }

    mock_driver, mock_session = create_mock_driver()
    
    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "delete_user", return_value=True) as mock_delete_user,
    ):
        response = client.delete(
            f"/users/{mock_users["email"]}"
        )
    
    assert response.status_code == 200
    assert response.json()["message"] == f"User '{mock_users["email"]}' deleted successfully."
    
def test_delete_user_not_found():
    mock_users = {
        "email": "jane@email.com",
        "real_name": "Jane Doe",
        "role": "Admin",
        "password": "hello world",
        "affiliation": "grey-box",
        "created_at": None
    }

    mock_driver, mock_session = create_mock_driver()
    
    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "delete_user", return_value=False) as mock_delete_user,
    ):
        response = client.delete(
            f"/users/abc"
        )
    
    assert response.status_code == 404
    assert response.json()["detail"] == f"User 'abc' not found."
    
def test_delete_user_exception_thrown():
    mock_driver, mock_session = create_mock_driver()
    
    with (
        patch.object(api, "driver", mock_driver),
        patch.object(api, "delete_user", side_effect=Exception("Some Exception Thrown")) as mock_delete_user,
    ):
        response = client.delete(
            f"/users/abc"
        )
    
    assert response.status_code == 500
    assert response.json()["detail"] == f"Some Exception Thrown"