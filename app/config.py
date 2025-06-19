from pydantic_settings import BaseSettings 



class Settings(BaseSettings):
    APIFY_TOKEN:str 
    ACTOR_ID:str 
    BACKEND_BASE:str
    OPENAI_API_KEY:str 
    GOOGLE_API_KEY:str

    class Config:
        env_file=".env"

settings=Settings()
