FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/ruimarj/nlalpha" \
      org.opencontainers.image.description="Install-and-use bundle for the NLAlpha quantitative research stack" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md README.zh.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir \
        --index-url "$PIP_INDEX_URL" \
        ${PIP_EXTRA_INDEX_URL:+--extra-index-url "$PIP_EXTRA_INDEX_URL"} \
        ${PIP_TRUSTED_HOST:+--trusted-host "$PIP_TRUSTED_HOST"} \
        '.[china]'

RUN useradd --create-home --uid 10001 nlalpha \
    && mkdir -p /state \
    && chown nlalpha:nlalpha /state
USER nlalpha

ENTRYPOINT ["nlalpha"]
CMD ["doctor"]
