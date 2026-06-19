import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # For instant local run we use SQLite. For MySQL, update backend/.env:
    # DATABASE_URL=mysql+pymysql://root:password@localhost:3306/awams_db
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./awams.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")


settings = Settings()
