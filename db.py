from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Boolean, PickleType, DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker

from config import Config

Base = declarative_base()
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

used_codes = Table(
    'used_codes', Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('code_id', Integer, ForeignKey('code.id'))
)


class Code(Base):
    __tablename__ = 'code'
    id = Column(Integer, primary_key=True)
    code = Column(String, index=True, unique=True)
    expired = Column(Boolean, index=True, default=False)
    used_by = relationship('User', secondary=used_codes,
                            back_populates='used', lazy='dynamic')

    def __repr__(self):
        return f'<Code {self.code}>'


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    uid = Column(Integer, index=True, unique=True)
    chat_id = Column(Integer, index=True, unique=True)
    cookie = Column(PickleType)
    cookie_expiry = Column(DateTime)
    used = relationship('Code', secondary=used_codes,
                        back_populates='used_by', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.uid}>'

    def redeem_code(self, code):
        if not self.redeemed(code):
            self.used.append(code)

    def redeemed(self, code):
        return self.used.filter(used_codes.c.code_id == code.id).count() > 0

Base.metadata.create_all(engine)
Session = sessionmaker(engine)