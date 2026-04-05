from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: Optional[str] = None
    telegram_chat_id: int                                   
    watchlist: list[str]                                      
    is_active: bool                                    
