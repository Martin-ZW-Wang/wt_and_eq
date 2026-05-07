# 地震與台北天氣 Discord 自動通知系統

## 1. 功能總覽

此專案會透過 GitHub Actions 執行 Python 程式，查詢台灣附近地震與台北市 12 個行政區天氣，並把結果傳送到 Discord。

目前功能：

- 查詢台灣附近最近地震狀態
- 查詢台北市 12 個行政區天氣
- 顯示天氣現象、最高溫度、最低溫度、降雨機率
- 根據天氣狀態附上對應圖片
- 使用 Discord Webhook 發送通知
- 使用 GitHub Secrets 儲存 API Key 與 Webhook
- 可手動執行
- 可 Push 後自動執行
- 可設定每天台灣時間自動執行

---

## 2. 專案檔案結構

```text
專案根目錄/
├── earthquake_notify.py
├── README.md
└── .github/
    └── workflows/
        └── earthquake_weather.yml
```

| 檔案 | 說明 |
|---|---|
| `earthquake_notify.py` | 主程式，負責查詢地震、天氣、選擇天氣圖片並發送 Discord |
| `.github/workflows/earthquake_weather.yml` | GitHub Actions 設定檔，負責執行 Python 程式 |

---

## 3. 需要設定的 GitHub Secrets

到 GitHub Repository：

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

新增以下兩個 Secret。

### DISCORD_WEBHOOK_URL

| 欄位 | 內容 |
|---|---|
| Name | `DISCORD_WEBHOOK_URL` |
| Secret | Discord Webhook URL |

格式範例：

```text
https://discord.com/api/webhooks/一串數字/一長串token
```

### CWA_AUTHORIZATION

| 欄位 | 內容 |
|---|---|
| Name | `CWA_AUTHORIZATION` |
| Secret | 中央氣象署 CWA API 授權碼 |

格式範例：

```text
CWA-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## 4. Python 主要設定

在 `earthquake_notify.py` 中，API Key 與 Webhook 透過環境變數讀取：

```python
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
CWA_AUTHORIZATION = os.getenv("CWA_AUTHORIZATION", "")
```

代表這兩個值會由 GitHub Secrets 傳入，不需要直接寫在程式碼中。

---

## 5. 可調整參數

```python
SEARCH_RADIUS_KM = 500
EARTHQUAKE_LOOKBACK_MINUTES = 10
DISTRICT_INTERVAL_SECONDS = 5
CYCLE_INTERVAL_SECONDS = 30
MAX_CYCLES = 1
```

| 參數 | 說明 |
|---|---|
| `SEARCH_RADIUS_KM` | 地震查詢半徑，單位公里 |
| `EARTHQUAKE_LOOKBACK_MINUTES` | 查詢最近幾分鐘內的地震 |
| `DISTRICT_INTERVAL_SECONDS` | 每個行政區之間等待幾秒 |
| `CYCLE_INTERVAL_SECONDS` | 每一輪結束後等待幾秒 |
| `MAX_CYCLES` | 總共執行幾輪 |

建議設定：

```python
MAX_CYCLES = 1
```

如果設太大，GitHub Actions 可能會因為執行太久被取消。

---

## 6. 台北市行政區輪巡順序

程式會依序查詢：

```text
中正區
大同區
中山區
松山區
大安區
萬華區
信義區
士林區
北投區
內湖區
南港區
文山區
```

每查詢完一個行政區，就會發送一次 Discord 通知。

---

## 7. 天氣圖片判斷

程式會根據中央氣象署回傳的天氣文字，自動選擇圖片。

| 天氣文字包含 | 對應圖片 |
|---|---|
| 晴 | 晴天圖片 |
| 晴、雲、陰 | 晴時多雲圖片 |
| 多雲 | 多雲圖片 |
| 陰 | 陰天圖片 |
| 雨、陣雨 | 雨天圖片 |
| 雷 | 雷雨圖片 |
| 雪 | 雪天圖片 |
| 霧、靄 | 霧天圖片 |

圖片會透過 Discord embed 顯示。

---

## 8. Discord 通知格式

Discord 會收到類似以下內容：

```text
📢 地震與台北天氣自動通知
更新時間：2026-05-05 18:41:00（台灣時間）
目前行政區：第 1 / 12 區
本次行政區：台北市 中正區

🌏 地震狀態
最近 10 分鐘內，台灣附近 500 公里內沒有查詢到地震。

🌤️ 台北市 中正區 今日天氣狀態
🖼️ 本次天氣圖片判斷：多雲
白天：多雲，23–28°C，降雨機率 20%
晚上：陰時多雲，22–25°C，降雨機率 30%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 9. GitHub Actions 執行方式

### Push 後自動執行

只要修改檔案並 Commit，GitHub Actions 會自動執行。

```text
修改檔案
→ Commit changes
→ Actions 自動執行
```

### 手動執行

```text
GitHub Repository
→ Actions
→ Earthquake and Taipei Weather Discord Notify
→ Run workflow
```

### 每天台灣時間 18:41 自動執行

GitHub Actions cron 使用 UTC 時間。

```text
台灣時間 18:41 = UTC 10:41
```

在 `.github/workflows/earthquake_weather.yml` 中設定：

```yaml
on:
  workflow_dispatch:

  schedule:
    - cron: "41 10 * * *"
```

如果還想保留 Push 後自動執行，可以使用：

```yaml
on:
  push:
    branches:
      - main
      - master

  workflow_dispatch:

  schedule:
    - cron: "41 10 * * *"
```

---

## 10. GitHub Actions 正常執行判斷

到 GitHub：

```text
Actions
→ 最新一次執行紀錄
→ notify
→ Run Python script
```

正常會看到：

```text
開始執行 Python 程式
找到根目錄 earthquake_notify.py
地震與台北天氣 Discord 自動通知系統已啟動。
目前查詢行政區：台北市 中正區
Discord 回應狀態碼：204
Discord 訊息已送出。
```

只要看到：

```text
Discord 回應狀態碼：204
Discord 訊息已送出。
```

代表 Discord Webhook 已成功發送。

---

## 11. 常見錯誤

| 錯誤訊息 | 原因 | 處理方式 |
|---|---|---|
| `Invalid URL ''` | 沒有讀到 Discord Webhook | 檢查 `DISCORD_WEBHOOK_URL` Secret |
| `401 Unauthorized` | 沒有讀到 CWA 授權碼或授權碼錯誤 | 檢查 `CWA_AUTHORIZATION` Secret |
| `找不到 earthquake_notify.py` | Python 檔名或位置錯誤 | 確認檔案在根目錄或 yml 指定位置 |
| `ValueError: too many values to unpack` | 回傳值接收數量錯誤 | 確認使用 `message, image_url = build_status_message(...)` |
| `name 'image_url' is not defined` | 沒有正確接收圖片網址 | 確認 `build_status_message()` 有回傳 `image_url` |
| `The job has exceeded the maximum execution time` | 執行太久 | 降低 `MAX_CYCLES` 或增加 `timeout-minutes` |
| Discord 沒收到訊息 | Webhook 錯誤、Secret 錯誤或看錯頻道 | 查看 Actions Log 是否有狀態碼 `204` |
