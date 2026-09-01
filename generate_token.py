#!/usr/bin/env python
"""Generate a valid JWT token for testing."""
import sys
sys.path.insert(0, "backend")

from app.dependencies import create_access_token
import uuid

# Create a valid token for an admin user
user_id = str(uuid.uuid4())
token = create_access_token({"sub": user_id, "role": "admin"})
print(f"Valid JWT Token (copy this):\n{token}\n")
