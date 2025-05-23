FROM python:3.12-slim

# تثبيت الأدوات اللازمة لبناء الحزم
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    build-essential \
    python3-dev \
    && apt-get clean

# إنشاء بيئة افتراضية
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# نسخ ملفات المشروع
WORKDIR /app
COPY . /app

# تثبيت المتطلبات
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# أمر التشغيل (غيّره حسب مشروعك)
CMD ["python", "bot.py"]
