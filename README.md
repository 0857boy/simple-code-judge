# 簡單程式自動化測試

這是一個簡單的程式自動化測試系統，使用 Flask 框架來建立後端伺服器，並提供上傳、匯出、匯入、刪除測試資料及提交程式碼進行測試的功能。

## 專案結構

- `app.py`：後端伺服器的主要程式碼，處理各種 API 請求。
- `index.html`：前端介面，提供使用者與系統互動的網頁。
- `Dockerfile`：用於建立 Docker 映像檔的設定檔。
- `README.md`：專案說明文件。

## 功能

1. **上傳測試資料**：上傳 `.in` 和 `.out` 檔案作為測試資料。
2. **列出測試資料**：列出所有已上傳的測試資料。
3. **匯出測試資料**：將所有測試資料打包成 ZIP 檔案下載。
4. **匯入測試資料**：上傳含有 .in 和 .out 的資料夾匯入測試資料。
5. **刪除測試資料**：刪除指定的測試資料。
6. **提交程式碼**：提交程式碼並選擇語言（C++、Java、Python），系統會自動執行程式並比對輸出結果。

## 使用方法

### 使用 Docker 執行

1. 拉取並啟動容器：

    - 僅允許本機(localhost)使用
        ```sh
        docker run -d -p 127.0.0.1:5000:5000 -v judge_testcases:/app/testcases --name judge ghcr.io/0857boy/simple-code-judge:latest
        ```
    - 供外部連線使用
        ```sh
        docker run -d -p 5000:5000 -v judge_testcases:/app/testcases --name judge ghcr.io/0857boy/simple-code-judge:latest
        ```
2. 開啟瀏覽器並訪問 `http://localhost:5000` 使用前端介面。



## API 端點

- `GET /`：檢查伺服器狀態。
- `POST /upload`：上傳測試資料。
- `GET /testcases`：列出測試資料。
- `GET /testcases/<name>`：取得特定測試資料。
- `GET /export`：匯出測試資料。
- `POST /import`：匯入測試資料。
- `POST /delete`：刪除測試資料。
- `POST /judge`：提交程式碼進行測試。

## 貢獻

歡迎提交問題或請求功能，您可以透過提交 Pull Request 來貢獻您的代碼。