"""AWS Lambda entry point (Mangum + FastAPI)."""
from mangum import Mangum

from api.main import app

handler = Mangum(app, lifespan="off")
