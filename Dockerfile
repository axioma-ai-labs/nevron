# ==================
# Build Nevron Agent
# ==================

FROM python:3.13-slim
WORKDIR /nevron

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

# -----------------------
# Install system packages
# -----------------------

RUN apt-get update && apt-get install -y \
    curl \
    git \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Configure Poetry
RUN poetry config virtualenvs.create false

# -------------------------
# Create the logs directory
# -------------------------

RUN mkdir logs

# ---------------------
# Setup the environment
# ---------------------

COPY pyproject.toml poetry.lock ./

<<<<<<< HEAD
# Install dependencies with Poetry
RUN poetry install --no-interaction --no-ansi --no-root --only main
=======
# Install other dependencies with Poetry
RUN poetry install --no-interaction --no-ansi --no-root
>>>>>>> e4f134c (Integrate llama embeddings (#116))

# --------------
# Nevron Runtime
# --------------

COPY . /nevron

COPY entrypoint.sh /nevron/entrypoint.sh
RUN chmod +x /nevron/entrypoint.sh

# Command to run the application
ENTRYPOINT ["/nevron/entrypoint.sh"]