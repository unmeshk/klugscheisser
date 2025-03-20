import logging
import asyncio
import signal
import uvicorn
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

from klugbot import KlugBot


# Initialize the FastAPI app
app = FastAPI()

 # Initialize bot
bot = KlugBot()

@app.post("/slack/events")
async def endpoint(request: Request):
    """Handle incoming Slack events."""
    return await bot.handler.handle(request)

@app.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}

# Set up shutdown handlers
async def shutdown_handler():
    """Handle application shutdown."""
    logger.info("Application shutting down...")
    await bot.shutdown()

app.router.add_event_handler("shutdown", shutdown_handler)

def handle_sigterm(*args):
    """Handle SIGTERM signal."""
    logger.info("Received SIGTERM signal")
    asyncio.create_task(bot.shutdown())

# Register signal handlers
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)


if __name__ == "__main__":
    # Verify required environment variables
    required_env_vars = [
        "SLACK_BOT_TOKEN", 
        "SLACK_SIGNING_SECRET",
        "GEMINI_API_KEY",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_PORT",
        "POSTGRES_IP",
        "POSTGRES_DB"
    ]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    if not os.getenv("KLUGBOT_LOG_CHANNEL"):
        logger.info("KLUGBOT_LOG_CHANNEL not set in env, using default from settings")

    # Run the server
    logger.info("Starting server")
    uvicorn.run(app, host="0.0.0.0", port=3000)