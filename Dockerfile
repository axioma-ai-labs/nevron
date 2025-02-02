# ==================
# Build Nevron Agent
# ==================

FROM python:3.12-slim
WORKDIR /nevron

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

# -----------------------
# Install system packages
# -----------------------

RUN apt-get update && apt-get install -y
#   git \
#   curl \
#   libxml2-dev \
#   libxslt-dev \
#   libjpeg-dev \
#   zlib1g-dev \
#   libpng12-dev \
#   && rm -rf /var/lib/apt/lists/*

RUN pip install pipenv

# -------------------------
# Create the logs directory
# -------------------------

RUN mkdir logs

# ---------------------
# Setup the environment
# ---------------------

COPY Pipfile Pipfile.lock 

RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

# --------------
# Nevron Runtime
# --------------

COPY . /nevron

# Command to run the application
CMD ["pipenv", "run", "python", "-m", "src.main"]
