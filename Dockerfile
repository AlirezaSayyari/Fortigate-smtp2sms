FROM python:3.11-slim
ENV PYTHONIOENCODING=utf-8
WORKDIR /app
ARG APP_FILE=smtp2sms_gateway.py
COPY ${APP_FILE} /app/smtp2sms_gateway.py
RUN pip install aiosmtpd requests python-dotenv
ENV PYTHONUNBUFFERED=1
EXPOSE 25
CMD ["python", "smtp2sms_gateway.py"]
