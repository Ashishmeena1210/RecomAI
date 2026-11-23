import os
from .base import *

DEBUG = False
DATABASES = {}                      # swap for Postgres in Stage 12
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")