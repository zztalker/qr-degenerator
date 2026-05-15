FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libzbar0 \
        libgl1 \
        libglib2.0-0 \
        nginx \
        gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY qr_processor.py app.py append.txt ./
COPY templates ./templates
COPY nginx.conf nginx-ssl.conf /app/
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000 8443

CMD ["/start.sh"]
