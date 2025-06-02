FROM python:3.11-slim

# 安裝必要的工具和所有支援的程式語言環境
RUN apt update && apt install -y \
    g++ \
    openjdk-17-jdk \
    nodejs \
    npm \
    golang-go \
    curl \
    wget \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# 建立非 root 使用者（在設定工作目錄之前）
RUN groupadd -r judge && useradd -r -g judge judge

# 設定工作目錄
WORKDIR /app

# 複製並安裝 Python 依賴
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼和資源
COPY app.py /app/app.py
COPY index.html /app/index.html
COPY favicons_io /app/favicons_io
COPY entrypoint.sh /app/entrypoint.sh

# 建立測試案例目錄並設定正確的擁有者和權限
RUN mkdir -p /app/testcases && \
    chown -R judge:judge /app && \
    chmod -R 755 /app && \
    chmod +x /app/entrypoint.sh

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# 開放 Flask 服務
EXPOSE 5000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 使用啟動腳本
CMD ["/app/entrypoint.sh"]
