# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Указываем переменные окружения
ENV PYTHONUNBUFFERED=1

# Указываем команду для запуска бота
CMD ["python", "main.py"]