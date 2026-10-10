import uvicorn
from config import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )
