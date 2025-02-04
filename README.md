# 簡單程式自動化測試

這是一個簡單的程式自動化測試系統，使用 Flask 框架來建立後端伺服器，並提供上傳、匯出、匯入、刪除測試資料及提交程式碼進行測試的功能。

## 專案結構

- `app.py`：後端伺服器的主要程式碼，處理各種 API 請求。
- `index.html`：前端介面，提供使用者與系統互動的網頁。
- `DockerFile`：用於建立 Docker 映像檔的設定檔。
- `README.md`：專案說明文件。

## 功能

1. **上傳測試資料**：上傳 `.in` 和 `.out` 檔案作為測試資料。
2. **列出測試資料**：列出所有已上傳的測試資料。
3. **匯出測試資料**：將所有測試資料打包成 ZIP 檔案下載。
4. **匯入測試資料**：上傳 ZIP 檔案並解壓縮匯入測試資料。
5. **刪除測試資料**：刪除指定的測試資料。
6. **提交程式碼**：提交程式碼並選擇語言（C++、Java、Python），系統會自動執行程式並比對輸出結果。

## 使用方法

### 使用 Docker 執行

1. 建立 Docker 映像檔：
    ```sh
    docker build -t simple-code-judge .
    ```

2. 啟動容器：
    ```sh
    docker run -p 5000:5000 simple-code-judge
    ```

3. 開啟瀏覽器並訪問 `http://localhost:5000` 使用前端介面。

### 手動執行

1. 安裝所需套件：
    ```sh
    pip install flask flask-cors
    ```

2. 啟動 Flask 伺服器：
    ```sh
    python app.py
    ```

3. 開啟瀏覽器並訪問 `http://localhost:5000` 使用前端介面。

## API 端點

- `GET /`：檢查伺服器狀態。
- `POST /upload`：上傳測試資料。
- `GET /testcases`：列出測試資料。
- `GET /export`：匯出測試資料。
- `POST /import`：匯入測試資料。
- `POST /delete`：刪除測試資料。
- `POST /judge`：提交程式碼進行測試。

## 貢獻

歡迎提交問題或請求功能，您可以透過提交 Pull Request 來貢獻您的代碼。
