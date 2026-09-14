from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = (
    "mysql+pymysql://2GextZHcx7NaoLC.root:vg5VNus3qKGeJdkK"
    "@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/test"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()