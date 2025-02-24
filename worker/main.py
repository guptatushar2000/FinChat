import uvicorn
from fastapi import FastAPI

from server import home

app = FastAPI()

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)
