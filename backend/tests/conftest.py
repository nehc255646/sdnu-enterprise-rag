import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_rag.db")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("QDRANT_URL", "")
os.environ.setdefault("QDRANT_PATH", "")
os.environ.setdefault("APP_ENV", "test")
