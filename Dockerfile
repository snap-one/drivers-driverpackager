FROM python:3.10

COPY entrypoint.sh /entrypoint.sh
COPY ./dp3 /app/dp3

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y python3-dev
RUN apt-get install -y swig
RUN apt-get install -y luajit
RUN pip install m2crypto
RUN pip install lxml

ENTRYPOINT ["/entrypoint.sh"]