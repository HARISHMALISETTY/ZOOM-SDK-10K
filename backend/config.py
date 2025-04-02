import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ZOOM_CLIENT_ID = os.getenv('ZOOM_CLIENT_ID')
    ZOOM_CLIENT_SECRET = os.getenv('ZOOM_CLIENT_SECRET')
    ZOOM_ACCOUNT_ID = os.getenv('ZOOM_ACCOUNT_ID')

    @classmethod
    def validate(cls):
        if not all([cls.ZOOM_CLIENT_ID, cls.ZOOM_CLIENT_SECRET, cls.ZOOM_ACCOUNT_ID]):
            raise ValueError("Missing required environment variables. Please check your .env file.")

settings = Settings() 