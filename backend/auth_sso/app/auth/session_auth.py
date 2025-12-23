from fastapi import Request

def get_current_user_session(request: Request) -> dict | None:
    """
    Returns the logged-in user stored in the signed session cookie.
    Structure example:
      {"id": 1, "email": "admin@example.com", "name": "Admin"}
    """
    return request.session.get("user")

def login_user_session(request: Request, user: dict) -> None:
    """
    Stores a minimal user payload in the session cookie.
    """
    request.session["user"] = user

def logout_user_session(request: Request) -> None:
    """
    Removes user data from the session cookie.
    """
    request.session.pop("user", None)
