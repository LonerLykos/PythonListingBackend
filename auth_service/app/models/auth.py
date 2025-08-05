from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime, timezone
import enum


class TokenType(enum.Enum):
    AUTH_ACCESS = 'auth_access'
    AUTH_REFRESH = 'auth_refresh'
    RESET_PASSWORD = 'reset_password'
    EMAIL_VERIFY = 'email_verify'


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=False)
    is_superadmin = Column(Boolean, default=False)


class ActiveToken(Base):
    __tablename__ = 'active_tokens'
    id = Column(Integer, primary_key=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token_type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BlacklistedToken(Base):
    __tablename__ = 'blacklisted_tokens'
    id = Column(Integer, primary_key=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    blacklisted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
