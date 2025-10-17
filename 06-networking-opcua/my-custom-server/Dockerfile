FROM python:3.12-slim
WORKDIR /app
RUN pip install opcua
COPY ./server.py /app/server.py
EXPOSE 4840
CMD ["python", "server.py"]
