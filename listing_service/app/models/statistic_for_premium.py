from sqlalchemy import Column, ForeignKey, Integer, Date, Float
from .base import Base


class ListingView(Base):
    __tablename__ = 'listing_views'
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey('listings.id'), index= True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    viewed_at = Column(Date, nullable=False, index=True)
