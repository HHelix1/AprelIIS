from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = "sqlite:///./employee_training.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import os
    db_file = "employee_training.db"

    if os.path.exists(db_file):
        logger.info(f"База данных {db_file} уже существует")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Существующие таблицы: {existing_tables}")
    else:
        logger.info(f"Создание новой базы данных: {db_file}")

    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы/проверены в базе данных")