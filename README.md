# 簡單程式自動化測試

這是一個簡單的程式自動化測試系統，使用 Flask 框架來建立後端伺服器，並提供上傳、匯出、匯入、刪除測試資料及提交程式碼進行測試的功能。

## 專案結構

- `app.py`：後端伺服器的主要程式碼，處理各種 API 請求。
- `index.html`：前端介面，提供使用者與系統互動的網頁。
- `favicon_io`：網站圖示。
- `Dockerfile`：用於建立 Docker 映像檔的設定檔。
- `README.md`：專案說明文件。

## 使用方法

### 使用 Docker 執行

1. 拉取並啟動容器：

    - 僅允許本機(localhost)使用
        ```sh
        docker run -d -p 127.0.0.1:5000:5000 -v judge_testcases:/app/testcases --name judge ghcr.io/0857boy/simple-code-judge
        ```
2. 開啟瀏覽器並訪問 `http://localhost:5000` 使用前端介面。

> **注意：** volume `judge_testcases` 用於保存測試資料，可以在容器重啟後保留測試資料，若刪除volume則會遺失所有測試資料。

## 功能

1. **新增測試資料** 
   ![addTestCase](/img/addTestCase.png)
   填寫測試資料名稱、輸入內容、預期輸出，並點擊上傳按鈕即可新增測試資料。
2. **管理測試資料**
   ![manageTestCase](/img/manageTestCase.png)
   可以預覽、刪除測試資料。
3. **匯入/匯出測試資料**
   ![importExport](/img/importExport.png)
   可以匯入、匯出所有測試資料。 
4. **提交程式碼進行測試**
   ![judge](/img/judge.png)
   填寫程式碼、選擇語言類別，並點擊測試按鈕即可進行測試。
5. **查看測試結果**
   ![rightResult](/img/rightResult.png)![errorResult](/img/ErrorResult.png)
   可以查看測試結果，包括預期輸出、實際輸出，並且依照簡單比對結果可以快速找到不同之處。
 
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