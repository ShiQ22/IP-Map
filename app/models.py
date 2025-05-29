# app/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    Boolean,
    ForeignKey,
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

class DeviceType(str, enum.Enum):
    pc      = "pc"
    laptop  = "laptop"
    mobile  = "mobile"
    tablet  = "tablet"
    wifi    = "wifi"
    other   = "other"

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
    department = Column(String(100), nullable=False, default="", server_default="")
class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    id           = Column(Integer, primary_key=True)
    account_name = Column(String(100), nullable=False)
    location     = Column(String(100), nullable=False)
    hostname     = Column(String(100), nullable=False)
    updated_by   = Column(Integer, ForeignKey("admins.id"), nullable=True)

class Server(Base, TimestampMixin):
    __tablename__ = "servers"
    id          = Column(Integer, primary_key=True)
    server_name = Column(String(100), nullable=False, unique=True)
    location    = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    
class IP(Base, TimestampMixin):
    __tablename__ = "ips"

    id           = Column(Integer, primary_key=True)
    ip_address   = Column(String(45), nullable=False)
    mac_address  = Column(String(50), nullable=True)
    asset_tag    = Column(String(50), nullable=True)
    snipe_id     = Column(Integer, nullable=True)
    # Fields for User-IP Management (and also used by devices/servers)
    department = Column(String(100), nullable=False, default="", server_default="")
    device_type  = Column(SQLEnum(DeviceType), nullable=False, default=DeviceType.other)
    updated_by   = Column(Integer, ForeignKey("admins.id"), nullable=True)

    owner_type   = Column(SQLEnum(OwnerType), nullable=False)
    owner_id     = Column(Integer, nullable=False)

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

class IPRange(Base, TimestampMixin):
    __tablename__ = "ip_ranges"

    id        = Column(Integer, primary_key=True)
    cidr      = Column(String(50), nullable=False, unique=True)
    active    = Column(Boolean, nullable=False, default=True)
