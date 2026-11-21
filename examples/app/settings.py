"""Demo settings module for `envdiff scan`."""

import os

APP_NAME = os.getenv("APP_NAME", "shop")
DEBUG = os.getenv("DEBUG") == "true"
DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL")
STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")  # added later, never documented
