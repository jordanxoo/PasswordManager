from pydantic_settings import BaseSettings                                               
from pydantic import ConfigDict
from pathlib import Path                                                                 
                  
print(Path(__file__).resolve().parent.parent.parent / ".env")

class Settings(BaseSettings):                                                            
      model_config = ConfigDict(
         env_file=Path(__file__).resolve().parent.parent.parent / ".env",
          extra="ignore"
      )

      DATABASE_URL: str                                                                    
      JWT_SECRET: str
      POSTGRES_USER: str                                                                   
      POSTGRES_PASSWORD: str
      POSTGRES_DB: str
      JWT_REFRESH_TOKEN: str
      ARGON2_TIME_COST: int = 3
      ARGON2_MEMORY_COST: int = 65536                                                      
   
settings = Settings()                                                                    
                  
print("DATABASE_URL:", settings.DATABASE_URL)
