FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install -r requirements.txt

COPY . .

EXPOSE 8050

# Run the app
CMD ["python", "ui.py"]