FROM python:3.14

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .
COPY predict.py .

CMD ["python", "main.py"]