# In: app/core/database/base.py

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# This is the single, shared MetaData instance for your entire application.
metadata_obj = MetaData()


class Base(DeclarativeBase):
    """The base class for all SQLAlchemy models."""

    metadata = metadata_obj
