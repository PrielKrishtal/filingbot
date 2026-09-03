
from pydantic import BaseModel


class User(BaseModel):
    username: str | None = None
    telegram_chat_id: int                                   
    watchlist: list[str]                                      
    is_active: bool                                    
