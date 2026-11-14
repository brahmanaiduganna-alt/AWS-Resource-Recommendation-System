from datetime import timezone


def iso(dt):
    """Return an ISO-8601 UTC string ending in Z, whether dt is naive or aware."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def public_user(user):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "organization": user.get("organization", ""),
        "created_at": iso(user.get("created_at")),
    }
