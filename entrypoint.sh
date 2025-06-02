#!/bin/bash

# 確保 testcases 目錄存在並設定正確權限
if [ -d "/app/testcases" ]; then
    # 檢查目錄擁有者，如果不是 judge 則修正
    if [ "$(stat -c %U /app/testcases)" != "judge" ]; then
        echo "Fixing testcases directory permissions..."
        chown -R judge:judge /app/testcases
        chmod -R 755 /app/testcases
    fi
else
    mkdir -p /app/testcases
    chown -R judge:judge /app/testcases
    chmod -R 755 /app/testcases
fi

# 切換到 judge 使用者並啟動應用程式
exec gosu judge gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 30 app:app 