FROM debian:bullseye

# Install uv
RUN apt-get update && apt-get install -y curl && rm -rf /var/cache/apt/archives /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN apt-get --purge autoremove -y curl
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml '/cimple/pyproject.toml'
COPY uv.lock '/cimple/uv.lock'

WORKDIR '/cimple'

RUN echo $PATH
RUN uv sync

# Add cimple system root to the System PATH
ENV PATH="/cimple-root/bin:$PATH"

COPY src '/cimple/src'

