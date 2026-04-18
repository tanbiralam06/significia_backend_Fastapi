import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.database.base import Base

# List only global system models for Master DB management
from app.models.user import User
from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.models.ia_master import IAMaster
from app.models.client import ClientProfile
from app.models.staff_profile import StaffProfile
from app.models.admin_activity_log import AdminActivityLog
from app.models.login_attempt import LoginAttempt

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from our app settings
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# target_metadata
target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    """
    Ensure we only migrate tables that belong to the Master Orchestrator.
    Business layer tables (silos) are managed separately.
    """
    if type_ == "table":
        # Only include tables present in the global Base metadata
        return name in target_metadata.tables
    return True

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
