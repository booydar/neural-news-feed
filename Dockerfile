FROM python:3.9-slim

# set a directory for the app
WORKDIR /app

# copy all the files to the container
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "./bot.py"]