"""Environment-backed settings for the local credit-intelligence MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv


MCP_DIR = Path(__file__).resolve().parent
load_dotenv(MCP_DIR.parent / "backend" / ".env")
load_dotenv(MCP_DIR / ".env", override=True)


# Parse DATABASE_URL / MCP_DATABASE_URL if present
_raw_db_url = os.getenv("MCP_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
_db_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
_db_port = int(os.getenv("POSTGRES_PORT", "5432"))
_db_name = os.getenv("POSTGRES_DB", "credit_dossier_mcp")
_db_user = os.getenv("POSTGRES_USER", "postgres")
_db_pass = os.getenv("POSTGRES_PASSWORD", "root")
_sslmode = os.getenv("POSTGRES_SSLMODE", "")

if _raw_db_url:
    # Normalize custom SQLAlchemy scheme prefix for standard urllib urlparse
    _url_for_parsing = _raw_db_url
    if _url_for_parsing.startswith("postgresql+psycopg://"):
        _url_for_parsing = "postgresql://" + _url_for_parsing[len("postgresql+psycopg://") :]
    elif _url_for_parsing.startswith("postgres://"):
        _url_for_parsing = "postgresql://" + _url_for_parsing[len("postgres://") :]

    try:
        _parsed = urlparse(_url_for_parsing)
        if _parsed.hostname:
            _db_host = _parsed.hostname
        if _parsed.port:
            _db_port = _parsed.port
        if _parsed.username:
            _db_user = unquote(_parsed.username)
        if _parsed.password is not None:
            _db_pass = unquote(_parsed.password)
        if _parsed.path and _parsed.path.strip("/"):
            _db_name = _parsed.path.strip("/")
        if not _sslmode and _parsed.query:
            _qs = parse_qs(_parsed.query)
            if "sslmode" in _qs:
                _sslmode = _qs["sslmode"][0]
    except Exception:
        pass


@dataclass(frozen=True)
class Settings:
    postgres_host: str = _db_host
    postgres_port: int = _db_port
    postgres_database: str = _db_name
    postgres_user: str = _db_user
    postgres_password: str = _db_pass
    postgres_sslmode: str = _sslmode
    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
    mistral_timeout_ms: int = int(os.getenv("MISTRAL_TIMEOUT_MS", "60000"))
    mcp_host: str = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("MCP_PORT", "8001"))
    mcp_transport: str = os.getenv("MCP_TRANSPORT", "sse")

    @property
    def is_cloud_database(self) -> bool:
        check_str = f"{self.postgres_host} {_raw_db_url}".lower()
        return any(cloud in check_str for cloud in ("neon.tech", "supabase", "cockroachlabs", "aivencloud"))

    def postgres_kwargs(self, database: str | None = None) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": database or self.postgres_database,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }
        if self.postgres_sslmode:
            kwargs["sslmode"] = self.postgres_sslmode
        elif self.is_cloud_database:
            kwargs["sslmode"] = "require"
        return kwargs


settings = Settings()
