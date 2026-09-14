# Backend: judge/app.py under uvicorn, via serve.py.
#
# WHY A DOCKERFILE RATHER THAN NIXPACKS
# --------------------------------------
# Railway's builder infers a stack from the repo. This repo has Python at the
# root and Node in `web/`, and the two services build from the same checkout -
# so inference has to be told which one it is looking at twice, and gets it
# right by accident rather than by declaration.
#
# The second reason is the one that matters more here. `pyproject.toml` says
# `requires-python = ">=3.11"`, which is a FLOOR, not a pin - this repo has run
# on 3.11 and 3.14 on the same machine. An inferred build picks whatever the
# builder's default is that week. `thread_context.offset_map` maps flattened
# offsets back to raw ones and `pyproject.toml` already argues at length that
# the text-producing stack must be reproducible; an interpreter that changes
# under the deployment is the same class of drift one layer down.
#
# So: pinned base image, declared install, no inference.

FROM python:3.11-slim

# `PYTHONUNBUFFERED` so `serve.py`'s startup lines - which database, which
# environment, whether API_TOKEN is set - reach the platform log immediately
# rather than sitting in a buffer while the container decides whether to live.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# DEPENDENCIES BEFORE SOURCE, so a code change does not reinstall the world.
# `pyproject.toml` alone is enough to resolve them; `README.md` comes too only
# because the metadata references it and the build fails without it.
COPY pyproject.toml README.md ./
# `.[dev]` is NOT installed. pytest and its plugins are not runtime
# dependencies, and a container that can run the suite is a container carrying
# code it will never execute.
RUN pip install --no-cache-dir .

# Source last. `.dockerignore` keeps `raw_store/` (257 MB), `_sweep_store/`
# (400 MB), `node_modules/` and `var/` out of the build context - without it
# this COPY ships two thirds of a gigabyte of harvested payloads into an image
# that reads them from a volume.
COPY . .

# DOCUMENTATION, NOT A BINDING. Railway assigns $PORT and `serve.py` reads it;
# this line is what `docker run -p 8000:8000` needs to be obvious locally.
EXPOSE 8000

# No shell form, so signals reach the process rather than a shell that ignores
# them - a container that cannot be stopped cleanly is a fetch that cannot
# write its own end record.
CMD ["python", "serve.py"]
