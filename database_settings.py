from email.policy import default
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, inspect
from sqlalchemy_utils import database_exists, create_database
import os
import time
import datetime


SQL_BINANCE_USERNAME = os.getenv('SQL_BINANCE_USERNAME')
SQL_BINANCE_PASSWORD = os.getenv('SQL_BINANCE_PASSWORD')


mysql_conn_str = f"mysql+pymysql://{SQL_BINANCE_USERNAME}:{SQL_BINANCE_PASSWORD}@binance_bot_creator_net:3306"

engine = create_engine(mysql_conn_str)


Base = declarative_base()
connection = engine.connect()

connection.execute("CREATE DATABASE IF NOT EXISTS instances")
connection.execute("commit")

mysql_conn_str = f"{mysql_conn_str}/instances?charset=utf8mb4"
engine = create_engine(mysql_conn_str, pool_recycle=3600)

Base = declarative_base()
connection = engine.connect()

# # Create database if it does not exist.
# with engine.connect() as conn:
#     # Do not substitute user-supplied database names here.
#     conn.execute(f"CREATE DATABASE IF NOT EXISTS INSTANCES")

sessionMade = sessionmaker(bind=engine)
session = Session(bind=engine)


class Sheet_Instance(Base):
    __tablename__ = "sheet_instance"

    id = Column(Integer, primary_key = True)
    api_key = Column(String(128))
    api_secret = Column(String(128))
    gid = Column(String(128))
    sheet_name = Column(String(128))
    sheet_name_lower = Column(String(128))
    active = Column(Boolean(), default=False)
    notification_chat_id = Column(String(128), default="-1001768606486")


Base.metadata.create_all(engine)

