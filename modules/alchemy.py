import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

Base = declarative_base()


class ChaturbateUser(Base):
    __tablename__ = 'CHATURBATE'
    username = Column(String(60), primary_key=True)
    chat_id = Column(String(100), primary_key=True)
    online = Column(Boolean)


class Admin(Base):
    __tablename__ = 'ADMIN'
    chat_id = Column(String(100), primary_key=True)


class PreferenceUser(Base):
    __tablename__ = 'PREFERENCES'
    chat_id = Column(String(100), primary_key=True)
    link_preview = Column(Integer, default=1)
    notifications_sound = Column(Boolean, default=True)


class Alchemy:
    def __init__(self, connection="postgresql://127.0.0.1:5432/ChaturbateBot"):
        self.connection = connection
        engine = create_engine(self.connection, echo=True)
        Base.metadata.create_all(engine)
        self.session: sqlalchemy.orm.Session = scoped_session(sessionmaker(bind=engine))
