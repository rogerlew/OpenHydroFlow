FROM ubuntu:24.04

RUN apt-get update \
&& apt-get install -y --no-install-recommends python3 python3-venv python3-pip \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
&& pip install --no-cache-dir -r requirements.txt

COPY epanet_util.py .
RUN python3 ./epanet_util.py
