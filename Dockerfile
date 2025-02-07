FROM python:3.9

# 安裝必要的工具
RUN apt update && apt install -y g++ openjdk-17-jdk

# 設定工作目錄
WORKDIR /app

# 安裝 Flask
RUN pip install flask flask-cors gunicorn

# 複製程式碼
COPY app.py /app/app.py

# 複製 favicon_io 資料夾
COPY favicons_io /app/favicons_io

# 複製網頁
COPY index.html /app/index.html

# 開放 Flask 服務
EXPOSE 5000

# 啟動 Flask 使用 Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
