from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_settings
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

settings = get_settings()


def _ensure_database_exists(db_url: str):
    """PostgreSQL 不会自动创建数据库，这里在连接前确保数据库存在"""
    parsed = urlparse(db_url)

    pg_schemes = ("postgresql", "postgresql+psycopg2", "postgresql+psycopg")
    if parsed.scheme not in pg_schemes:
        return  # MySQL 不需要自动创建

    db_name = parsed.path.lstrip("/")
    if not db_name:
        return

    try:
        # 尝试 psycopg v3，失败则尝试 psycopg2
        try:
            import psycopg
            conn = psycopg.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                user=parsed.username or "postgres",
                password=parsed.password or "",
                dbname="postgres",
                autocommit=True,
            )
        except ImportError:
            import psycopg2
            conn = psycopg2.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                user=parsed.username or "postgres",
                password=parsed.password or "",
                dbname="postgres",
            )
            conn.autocommit = True

        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"数据库 {db_name} 已创建")
        cur.close()
        conn.close()
    except ImportError:
        logger.warning("psycopg / psycopg2 未安装，跳过 PostgreSQL 数据库自动创建")
    except Exception as e:
        logger.warning(f"无法自动创建数据库 {db_name}: {e}")
        logger.warning(f"请手动创建: CREATE DATABASE {db_name};")


_ensure_database_exists(settings.database_url)


def _get_engine_kwargs(db_url: str) -> dict:
    """根据数据库类型返回优化的 engine 参数"""
    is_postgres = db_url.startswith("postgresql")

    kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "echo": False,
    }

    if is_postgres:
        # PostgreSQL 连接池优化
        kwargs.update({
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,  # PG 连接默认 30min 超时，提前回收
        })
    else:
        kwargs.update({
            "pool_recycle": 3600,  # MySQL 默认 8h 超时
        })

    return kwargs


engine = create_engine(
    settings.database_url,
    **_get_engine_kwargs(settings.database_url),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
