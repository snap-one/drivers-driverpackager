FROM python:3

COPY entrypoint.sh /entrypoint.sh
COPY ./dp3 /app/dp3

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y python3-dev
RUN apt-get install -y swig
RUN pip install m2crypto

ENTRYPOINT ["/entrypoint.sh"]