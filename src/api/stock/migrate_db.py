from sqlalchemy import create_engine

from stock.models.invest import Base

import os
from dotenv import load_dotenv

load_dotenv()

password = os.getenv("SUPABASE_PASSWORD")

print(password)

DB_URL = (
    f"postgresql://postgres.hfvsseitqggcevvyeerb:{password}@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
)
# DB_URL = "mysql+pymysql://root@db:3306/demo?charset=utf8"
engine = create_engine(DB_URL, echo=True)


def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    reset_database()
