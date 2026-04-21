FROM python:3.11-slim
ENV PYTHONIOENCODING=utf-8
WORKDIR /app
COPY smtp2sms_gateway.py /app
COPY .env /app
RUN pip install aiosmtpd requests python-dotenv
ENV PYTHONUNBUFFERED=1
EXPOSE 25
CMD ["python", "smtp2sms_gateway.py"]
