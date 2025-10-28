import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
from config.config import EnvConfig

Base = declarative_base()

encoded_user = quote_plus(EnvConfig.DB_USER)
encoded_pass = quote_plus(EnvConfig.DB_PASSWORD)
encoded_name = quote_plus(EnvConfig.DB_NAME)
encoded_server = quote_plus(EnvConfig.DB_SERVER)

DATABASE_URL = (
    f"mssql+pyodbc://{encoded_user}:{encoded_pass}@{encoded_server}/{encoded_name}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"❌ Error al crear el engine de SQLAlchemy: {e}")
    engine = None
    SessionLocal = None

def get_connection():
    try:
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={EnvConfig.DB_SERVER};"
            f"DATABASE={EnvConfig.DB_NAME};"
            f"UID={EnvConfig.DB_USER};"
            f"PWD={EnvConfig.DB_PASSWORD}"
        )
    except Exception as e:
        print(f"❌ Error al conectar con pyodbc directamente: {e}")
        return None
