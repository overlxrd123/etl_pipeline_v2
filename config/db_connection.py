"""
数据库连接工厂 — SQLAlchemy 引擎 + 会话管理
切换数据库只需改 .env 中的 DATABASE_URL
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import DB_URL

# SQLite 优化
ENGINE_KWARGS = {
    "echo": False,
    "future": True,
}
if "sqlite" in DB_URL:
    ENGINE_KWARGS["connect_args"] = {"check_same_thread": False}

engine = create_engine(DB_URL, **ENGINE_KWARGS)

# SQLite: 启用 WAL 模式 + 外键约束
if "sqlite" in DB_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_session():
    """获取数据库会话（用于手动脚本）"""
    return SessionLocal()


def init_db():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """删除所有表（谨慎使用）"""
    Base.metadata.drop_all(bind=engine)
