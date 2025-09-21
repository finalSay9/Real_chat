
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import Users,Auth, Messages, Conversation, WebSocketsRoutes



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.43.219:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(Auth.router)
app.include_router(Users.router)
app.include_router(Conversation.router)
app.include_router(Messages.router)
app.include_router(WebSocketsRoutes.router)