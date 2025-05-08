from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum as SQLEnum,
     Boolean,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base
import enum
import datetime

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False
    )

class RoleEnum(str, enum.Enum):
    admin = "admin"
    user  = "user"

class OwnerType(str, enum.Enum):
    user   = "user"
    device = "device"
    server = "server"

class Admin(Base, TimestampMixin):
    __tablename__ = "admins"
    id       = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    password = Column(String(200), nullable=False)
    role     = Column(SQLEnum(RoleEnum), nullable=False, default=RoleEnum.admin)

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    naos_id  = Column(String(50), nullable=False, unique=True)

class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    id           = Column(Integer, primary_key=True)
    account_name = Column(String(100), nullable=False)
    location     = Column(String(100), nullable=False)
    hostname     = Column(String(100), nullable=False)

class Server(Base, TimestampMixin):
    __tablename__ = "servers"
    id          = Column(Integer, primary_key=True)
    server_name = Column(String(100), nullable=False, unique=True)
    location    = Column(String(100), nullable=False)

class IP(Base, TimestampMixin):
    __tablename__ = "ips"
    id          = Column(Integer, primary_key=True)
    ip_address  = Column(String(45), nullable=False, unique=True)
    mac_address = Column(String(50), nullable=True)
    asset_tag   = Column(String(50), nullable=True)
    owner_type  = Column(SQLEnum(OwnerType), nullable=False)
    owner_id    = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "owner_type",
            "owner_id",
            "ip_address",
            name="uq_ip_owner"
        ),
    )

class LiveMonitor(Base):
    __tablename__ = "live_monitor"
    ip           = Column(String(45), primary_key=True)
    hostname     = Column(String(100), nullable=False)
    mac_address  = Column(String(50), nullable=False)
    vendor       = Column(String(100), nullable=False)
    status       = Column(String(10), nullable=False)
    last_checked = Column(DateTime, nullable=False)
    last_up      = Column(DateTime, nullable=True)

class History(Base):
    __tablename__ = "history"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ip          = Column(String(45), nullable=False)
    hostname    = Column(String(100), nullable=False)
    mac_address = Column(String(50), nullable=False)
    vendor      = Column(String(100), nullable=False)
    status      = Column(String(10), nullable=False)
    scan_time   = Column(DateTime, nullable=False)

# app/models.py

class IPRange(Base, TimestampMixin):
    __tablename__ = "ip_ranges"

    id        = Column(Integer, primary_key=True)
    cidr      = Column(String(50), nullable=False, unique=True)
    active    = Column(Boolean, nullable=False, default=True)
