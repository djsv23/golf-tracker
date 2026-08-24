FROM python:3.12-slim

LABEL maintainer="Daniel Steiner <djsteiner93@gmail.com>"

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	APP_DIR=/app \
	FLASK_APP=golf-tracker.py \
	FLASK_CONFIG=production

RUN groupadd --system appuser && useradd --system --gid appuser --uid 10001 appuser

WORKDIR ${APP_DIR}

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip \
	&& pip install -r requirements.txt

COPY . ${APP_DIR}

RUN mkdir -p /data \
	&& chown -R appuser:appuser ${APP_DIR} /data

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=3)"

CMD ["./boot.sh"]
