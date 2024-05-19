FROM python:3.12.3-alpine3.18

RUN apk update && apk upgrade && apk add bash && apk add openssh
RUN mkdir -p /app/logs
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "bot.py"]