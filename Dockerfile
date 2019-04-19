FROM alpine:3.9

LABEL maintainer="Daniel Steiner <djsteiner93@gmail.com>"

COPY requirements.txt requirements.txt

RUN apk update
RUN apk add --no-cache bash git nginx uwsgi uwsgi-python python3 py-pip python3-dev \
	&& pip3 install --upgrade pip \
	&& pip3 install --no-cache-dir -r requirements.txt

ENV APP_DIR /app
ENV FLASK_APP golf-tracker.py

RUN mkdir ${APP_DIR} 

COPY nginx.conf /etc/nginx/nginx.conf
COPY app.ini /app.ini


VOLUME ${APP_DIR}
WORKDIR ${APP_DIR}

COPY . ${APP_DIR}

RUN    chown -R nginx:nginx ${APP_DIR} \
	&& chmod 777 /run/ -R \
	&& chmod 777 /root/ -R

EXPOSE 5000

CMD ./boot.sh

