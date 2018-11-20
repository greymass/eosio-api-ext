FROM python:3.7.0-slim

RUN apt update && apt install -y gcc python3-dev

RUN pip3 install cython ujson
RUN pip3 install --no-binary :all: falcon

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /src/services/get_actions

CMD ["gunicorn", "--reload", "-c", "config.py", "main:app"]
