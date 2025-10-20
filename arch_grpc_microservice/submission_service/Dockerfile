FROM python:3.11-bullseye

WORKDIR /app
COPY submission_service/requirements.txt /app/requirements.txt
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_PROGRESS_BAR=off

RUN pip install --upgrade pip && \
    pip install --no-cache-dir --progress-bar off -r requirements.txt

COPY protos /app/protos
RUN python -m grpc_tools.protoc -I/app/protos --python_out=/app --grpc_python_out=/app /app/protos/api.proto

COPY submission_service/server.py /app/server.py

EXPOSE 50053
CMD ["python", "server.py"]
