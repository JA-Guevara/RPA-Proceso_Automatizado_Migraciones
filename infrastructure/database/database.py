import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.config import EnvConfig

logger = logging.getLogger(__name__)

Base = declarative_base()


def _resolver_database_url() -> str:
    if not EnvConfig.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL no está configurado. Define DATABASE_URL en el archivo .env."
        )

    return EnvConfig.DATABASE_URL


DATABASE_URL = _resolver_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

logger.info("🗄️ Engine SQLAlchemy inicializado.")