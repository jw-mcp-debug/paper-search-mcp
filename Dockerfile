# Multi-stage build for smaller image
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE requirements.txt setup.sh ./
COPY paper_search_mcp/ paper_search_mcp/

RUN bash setup.sh \
    && pip install --no-cache-dir build \
    && python -m build --wheel \
    && pip install --no-cache-dir dist/*.whl

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/paper-search-mcp /usr/local/bin/paper-search-mcp

ENV PORT=8000

EXPOSE 8000

# Use the entry point script
CMD ["paper-search-mcp"]
