from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Country(Base):
    __tablename__ = 'countries'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    regions = relationship("Region", back_populates="country")


class Region(Base):
    __tablename__ = 'regions_or_states'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)
    country = relationship("Country", back_populates="regions")
    cities = relationship("City", back_populates="region")


class City(Base):
    __tablename__ = 'cities'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    region_id = Column(Integer, ForeignKey('regions_or_states.id'), nullable=False)
    region = relationship("Region", back_populates="cities")
