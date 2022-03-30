FROM python:3.7
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && \
    apt install -y git vim openmpi-bin libopenmpi-dev libgl1 && \
    rm -rf /var/lib/apt/lists/*
