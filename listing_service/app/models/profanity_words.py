from sqlalchemy import Column, String, Integer
from .base import Base


class ProfanityWords(Base):
    __tablename__ = 'profanity_words'
    id = Column(Integer, primary_key=True)
    word = Column(String(100), unique=True, nullable=False, index=True)
