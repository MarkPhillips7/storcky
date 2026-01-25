"""
Initialize EdgarTools with identity (required by SEC).
This should be called once at application startup.
"""
from edgar import set_identity
import os

# Set identity for SEC compliance
# Users should set this in their environment or .env file
identity = os.getenv("EDGAR_IDENTITY", "storcky@example.com")
set_identity(identity)
