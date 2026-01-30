from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import sys
import os

# Ajouter le dossier parent au path pour importer les modèles
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importer la config de database
from src.db.database import DATABASE_URL

# Importer TOUS les modèles (crucial pour autogenerate)
from sqlmodel import SQLModel
from src.models.country import Country
from src.models.academy import Academy
from src.models.team import Team
from src.models.user import User
from src.models.catapult import CatapultSession

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the SQLAlchemy URL from database.py
config.set_main_option('sqlalchemy.url', DATABASE_URL)
target_metadata = SQLModel.metadata

# Configure l'import automatique de sqlmodel dans les migrations
def render_item(type_, obj, autogen_context):
    """Ajoute import sqlmodel si nécessaire"""
    if hasattr(obj, '__module__') and 'sqlmodel' in obj.__module__:
        autogen_context.imports.add("import sqlmodel")
    return False

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
