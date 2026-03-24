from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    username = Column(String)
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    gold = Column(Integer, default=1000)
    diamond = Column(Integer, default=100)
    health = Column(Integer, default=100)
    max_health = Column(Integer, default=100)
    attack = Column(Integer, default=10)
    defense = Column(Integer, default=5)
    weapon_id = Column(Integer, ForeignKey('items.id'), nullable=True)
    armor_id = Column(Integer, ForeignKey('items.id'), nullable=True)
    hero_id = Column(Integer, ForeignKey('heroes.id'), nullable=True)
    married_to = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory = relationship('Inventory', back_populates='user')
    items_owned = relationship('Inventory', cascade='all, delete-orphan')
    marriage = relationship('Marriage', foreign_keys='Marriage.user1_id', back_populates='user1')
    
class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    item_type = Column(String)  # weapon, armor, consumable
    description = Column(String)
    price = Column(Integer)
    attack_bonus = Column(Integer, default=0)
    defense_bonus = Column(Integer, default=0)
    health_bonus = Column(Integer, default=0)
    photo_id = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class Hero(Base):
    __tablename__ = 'heroes'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    attack_bonus = Column(Integer)
    defense_bonus = Column(Integer)
    health_bonus = Column(Integer)
    price = Column(Integer)
    photo_id = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    quantity = Column(Integer, default=1)
    
    user = relationship('User', back_populates='inventory')
    item = relationship('Item')
    
class Marriage(Base):
    __tablename__ = 'marriages'
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id'))
    user2_id = Column(Integer, ForeignKey('users.id'))
    married_at = Column(DateTime, default=datetime.utcnow)
    
    user1 = relationship('User', foreign_keys=[user1_id])
    user2 = relationship('User', foreign_keys=[user2_id])

class GlobalTop(Base):
    __tablename__ = 'global_top'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True)
    total_points = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class MarketListing(Base):
    __tablename__ = 'market_listings'
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey('users.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    price = Column(Integer)
    quantity = Column(Integer)
    listed_at = Column(DateTime, default=datetime.utcnow)
    
    seller = relationship('User')
    item = relationship('Item')

Base.metadata.create_all(engine)
