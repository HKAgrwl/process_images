from fastapi import FastAPI
from server.routes import router
from server.database import initialize_database

app = FastAPI()

# Initializing database
initialize_database()

# Including API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)