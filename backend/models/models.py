from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    embedding_settings = Column(JSONB, server_default='{}', nullable=False)
    prompt_templates = Column(JSONB, server_default='{}', nullable=False)
    state = Column(String(20), server_default="new", nullable=False)
    last_run_at = Column(DateTime(timezone=True))
    error_count = Column(Integer, server_default='0', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="datasets", lazy="selectin")
    settings = relationship("DatasetSettings", back_populates="dataset", uselist=False, lazy="selectin")

class DatasetSettings(Base):
    __tablename__ = "dataset_settings"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), unique=True, nullable=False)
    chunk_size = Column(Integer, default=512, nullable=False)
    chunk_overlap = Column(Integer, default=50, nullable=False)
    summary_prompt = Column(Text, default="Сделай краткое резюме текста.", nullable=False)
    metadata_targets = Column(JSONB, server_default='[]', nullable=False)
    gpt_model = Column(String(32), default="gpt-3.5-turbo", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset", back_populates="settings", lazy="selectin")

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    url = Column(Text, nullable=False)
    status = Column(String(20), server_default="queued", nullable=False)
    http_code = Column(Integer)
    last_attempt_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset", backref="links", lazy="selectin")

class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    raw_html = Column(Text, nullable=False)
    clean_text = Column(Text)
    raw_author = Column(Text)
    clean_author = Column(Text)
    author_needs_review = Column(Boolean, server_default='false', nullable=False)
    raw_date = Column(Text)
    clean_date = Column(DateTime(timezone=True))
    date_needs_review = Column(Boolean, server_default='false', nullable=False)
    raw_category = Column(Text)
    clean_category = Column(Text)
    category_needs_review = Column(Boolean, server_default='false', nullable=False)
    meta_data = Column(JSONB, server_default='{}', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    link = relationship("Link", backref="pages", lazy="selectin")

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    summary = Column(Text)
    clean_author = Column(String)
    chunk_meta_data = Column(JSONB, server_default='{}', nullable=False)
    quality = Column(String(32))  # был Integer, заменил на строку — потому что ты пишешь 'ok' и 'needs_review'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    page = relationship("Page", backref="chunks", lazy="selectin")

class Embedding(Base):
    __tablename__ = "embeddings"
    chunk_id = Column(Integer, ForeignKey("chunks.id"), primary_key=True)
    input = Column(Text, nullable=False)
    vector = Column(Vector(1536), nullable=False)
    embed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunk = relationship("Chunk", backref="embedding", lazy="selectin")