from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, DateTime, Integer, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

CST = timezone(timedelta(hours=8), name="Asia/Shanghai")

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def now_cst() -> datetime:
    # 全库统一存东八区 naive datetime，避免 MySQL server_default 在 async 下触发 MissingGreenlet
    return datetime.now(CST).replace(tzinfo=None)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now_cst,
        onupdate=now_cst,
        nullable=False,
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="乐观锁版本号")

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, object]:
        # 由 SQLAlchemy 在 UPDATE 时自动附加 version 条件并递增，避免读后写竞态
        return {"version_id_col": cls.version}
