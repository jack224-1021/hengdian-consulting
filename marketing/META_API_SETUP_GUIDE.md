# Meta API 全自動發文設定手冊（恒典管理顧問有限公司）

本手冊帶您一步步取得 **Facebook 粉絲專頁**、**Instagram 商業帳號** 與 **Threads** 的官方發文權杖（Token），填入 `.env` 後即可全自動每週發文。

> **安全提醒**：`.env` 檔案已設定在 `.gitignore` 中，**絕對不會**被上傳到公開的 GitHub 網站，請放心存放於本機電腦。

---

## 事前準備（5 分鐘檢查）

1. **Facebook 粉絲專頁**：確認已建立「恒典管理顧問有限公司」粉絲專頁。
2. **Instagram 商業帳號**：
   - 在 IG 手機 App → 設定 → 帳號類型和工具 → 切換為「**專業帳號（商業）**」。
   - 在 IG 設定 → 帳號管理中心 → 將此 IG 帳號**連結到您的 Facebook 粉絲專頁**。
3. **Threads 帳號**：使用同一個 IG 帳號開通 Threads。

---

## 第一步：建立 Meta 開發者應用程式

1. 前往 [Meta for Developers](https://developers.facebook.com/) 並登入您的 Facebook 帳號。
2. 點擊右上角「**我的應用程式**」→「**建立應用程式**」。
3. 應用程式名稱填寫：`HengDian Auto Marketing`。
4. 用途選擇「**其他**」→ 類型選擇「**商業（Business）**」→ 建立。
5. 在應用程式儀表板加入以下產品：
   - **Facebook 登入企業版**（或 Graph API）
   - **Instagram**
   - **Threads API**（如需自動發 Threads）

---

## 第二步：取得 Facebook 粉專與 IG 的 ID 與 Token

1. 打開官方工具：[Graph API 測試工具 (Graph API Explorer)](https://developers.facebook.com/tools/explorer/)。
2. 右側「Meta 應用程式」選擇剛建立的 `HengDian Auto Marketing`。
3. 右側「權限」依序勾選：
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `instagram_basic`
   - `instagram_content_publish`
4. 點擊藍色按鈕「**Generate Access Token**」，並勾選授權「恒典管理顧問有限公司」粉專與 IG 帳號。
5. 查詢您的 **粉專 ID** 與 **粉專 Token**：
   - 在上方網址列輸入：`me/accounts?fields=id,name,access_token,instagram_business_account`
   - 點擊「**提交**」，結果中即可看到：
     - `id` → 這是 **`FB_PAGE_ID`**
     - `access_token` → 這是 **`FB_PAGE_ACCESS_TOKEN`**
     - `instagram_business_account.id` → 這是 **`IG_USER_ID`**

> **進階小技巧（延長 Token 有效期）**：
> 預設的粉專 Token 約 1 小時過期。您可以前往 [存取權杖偵錯工具](https://developers.facebook.com/tools/debug/accesstoken/)，貼上剛取得的 User Token，點底部「**延長存取權杖**」轉成 60 天長期 Token，再重新呼叫 `me/accounts` 取得的粉專 Token 即為**永久有效（永不過期）**！

---

## 第三步：取得 Threads ID 與 Token（選配）

1. 在 Meta 應用程式後台 → **Threads API** → 權限勾選 `threads_basic` 與 `threads_content_publish`。
2. 透過 Threads 測試工具取得您的：
   - **`THREADS_USER_ID`**
   - **`THREADS_ACCESS_TOKEN`**（長期權杖有效 60 天）

---

## 第四步：填入 `.env` 並啟動測試

1. 在 `hengdian-website\marketing\` 資料夾中，複製 `.env.example` 並重新命名為 `.env`。
2. 用記事本打開 `.env`，填入上述取得的 5 組數值並存檔：

```env
FB_PAGE_ID=你的粉專數字ID
FB_PAGE_ACCESS_TOKEN=你的粉專永久Token
IG_USER_ID=你的IG商業帳號數字ID
THREADS_USER_ID=你的Threads數字ID
THREADS_ACCESS_TOKEN=你的Threads長期Token
```

3. 打開終端機（或在 Antigravity 直接跟我說「幫我正式發本週推廣文」）：
   - **安全預覽模式**（不發文，只產圖與預覽頁）：
     ```powershell
     C:\Users\iakhs0965\py311\python.exe run_weekly_post.py --dry-run
     ```
   - **正式自動發文模式**（自動推送小卡並發佈到 FB / IG / Threads）：
     ```powershell
     C:\Users\iakhs0965\py311\python.exe run_weekly_post.py --publish
     ```

---

## 每週自動排程建議

設定好 `.env` 後，您可以直接在 Antigravity 輸入 `/schedule`，設定 **每週三上午 09:00** 自動執行 `run_weekly_post.py --publish`，系統就會每週自動輪播 `config/topics.json` 中的下一篇主題、產圖並完成發文！
