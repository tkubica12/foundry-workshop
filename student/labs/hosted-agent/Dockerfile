FROM python:3.13.15-slim
WORKDIR /app
COPY requirements.lock .
RUN python -m pip install --no-cache-dir --require-hashes \
    --index-url https://packagefeedproxy.microsoft.io/pypi/simple/ -r requirements.lock
COPY agent.py system-prompt.txt ./
EXPOSE 8088
CMD ["python", "agent.py"]
