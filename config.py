import os

# The log folder location
LOG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs")

# Set log level to debug
DEBUG = True

# Generate with os.urandom(24)
SECRET_KEY = "SUPERSECRETKEY"

# Needed if application is not mounted in root
APPLICATION_ROOT = ""
