import os
import time
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
# ============================================================
# GitHub Actions / 本機共用設定
# ============================================================
# Discord Webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# 中央氣象署 CWA API 授權碼
# GitHub Actions 會從 Repository Secrets 讀取
CWA_AUTHORIZATION = os.getenv("CWA_AUTHORIZATION", "")

# 台北市天氣 API
CWA_TAIPEI_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063"

# 台北市行政區
DISTRICT_NAME = "中正區"

# USGS 地震 API
USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# 台灣中心座標
TAIWAN_LATITUDE = 23.6978
TAIWAN_LONGITUDE = 120.9605

# 查詢台灣附近幾公里內的地震
SEARCH_RADIUS_KM = 500

# 查詢最近幾分鐘內的地震
EARTHQUAKE_LOOKBACK_MINUTES = 10

# 每 10 秒發送一次 Discord 狀態
CHECK_INTERVAL_SECONDS = 10

# GitHub Actions 單次啟動後要跑幾次
# 28 次約 280 秒，接近 5 分鐘，但比較不容易和下一次排程重疊
LOOP_COUNT = int(os.getenv("LOOP_COUNT", "28"))

# 台灣時區
TAIWAN_TZ = ZoneInfo("Asia/Taipei")
# ============================================================
# Discord 發送函式
# ============================================================
def push_to_discord(message: str) -> None:

    if not DISCORD_WEBHOOK_URL:
        print("尚未設定 DISCORD_WEBHOOK_URL，無法發送。")
        return

    payload = {
        "content": message
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)

        if response.status_code in [200, 204]:
            print("Discord 訊息已送出。")
        else:
            print(f"Discord 發送失敗，狀態碼：{response.status_code}")
            print(response.text)

    except requests.RequestException as error:
        print(f"Discord 發送錯誤：{error}")

# ============================================================
# 台北天氣 API
# ============================================================
def fetch_taipei_weather(district: str) -> list:

    if not CWA_AUTHORIZATION:
        raise ValueError("尚未設定 CWA_AUTHORIZATION。")

    params = {
        "Authorization": CWA_AUTHORIZATION,
        "LocationName": district,
        "ElementName": "天氣現象,最高溫度,最低溫度,12小時降雨機率",
        "format": "JSON",
    }

    response = requests.get(CWA_TAIPEI_API_URL, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    return data["records"]["Locations"][0]["Location"][0]["WeatherElement"]
def parse_today_weather(elements: list) -> list[dict]:

    today_str = datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d")

    by_name = {}

    for elem in elements:
        by_name[elem["ElementName"]] = elem["Time"]

    weather_times = by_name.get("天氣現象", [])

    result = []

    for i, item in enumerate(weather_times):
        if not item["StartTime"].startswith(today_str):
            continue

        slot = {
            "start": item["StartTime"],
            "end": item["EndTime"],
            "weather": item["ElementValue"][0].get("Weather", "未知"),
            "max_temp": by_name["最高溫度"][i]["ElementValue"][0].get("MaxTemperature", "?"),
            "min_temp": by_name["最低溫度"][i]["ElementValue"][0].get("MinTemperature", "?"),
            "rain_prob": by_name["12小時降雨機率"][i]["ElementValue"][0].get("ProbabilityOfPrecipitation", "?"),
        }

        result.append(slot)

    return result
def format_weather_message() -> str:

    try:
        elements = fetch_taipei_weather(DISTRICT_NAME)
        slots = parse_today_weather(elements)

        if not slots:
            return (
                f"🌤️ **台北市 {DISTRICT_NAME} 天氣狀態**\n"
                "目前沒有取得今天剩餘時段的天氣資料。"
            )

        lines = [
            f"🌤️ **台北市 {DISTRICT_NAME} 今日天氣狀態**"
        ]

        for slot in slots:
            hour = int(slot["start"][11:13])
            label = "白天" if 6 <= hour < 18 else "晚上"

            lines.append(
                f"**{label}：** {slot['weather']}，"
                f"{slot['min_temp']}–{slot['max_temp']}°C，"
                f"降雨機率 {slot['rain_prob']}%"
            )

        return "\n".join(lines)

    except Exception as error:
        return (
            "🌤️ **台北天氣狀態**\n"
            f"取得天氣資料失敗：{error}"
        )
# ============================================================
# 地震 API
# ============================================================
def fetch_earthquakes() -> list:

    now_utc = datetime.now(timezone.utc)
    start_time = now_utc - timedelta(minutes=EARTHQUAKE_LOOKBACK_MINUTES)

    params = {
        "format": "geojson",
        "starttime": start_time.isoformat(),
        "endtime": now_utc.isoformat(),
        "latitude": TAIWAN_LATITUDE,
        "longitude": TAIWAN_LONGITUDE,
        "maxradiuskm": SEARCH_RADIUS_KM,
        "orderby": "time",
    }

    response = requests.get(USGS_API_URL, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    return data.get("features", [])
def format_earthquake_event(event: dict) -> str:

    properties = event.get("properties", {})
    geometry = event.get("geometry", {})
    coordinates = geometry.get("coordinates", [None, None, None])

    event_id = event.get("id", "未知 ID")
    place = properties.get("place", "未知地點")
    magnitude = properties.get("mag", "未知")
    event_time_ms = properties.get("time")
    detail_url = properties.get("url", "無詳細連結")

    longitude = coordinates[0]
    latitude = coordinates[1]
    depth = coordinates[2]

    if event_time_ms:
        event_time_utc = datetime.fromtimestamp(event_time_ms / 1000, tz=timezone.utc)
        event_time_taiwan = event_time_utc.astimezone(TAIWAN_TZ)
        event_time_text = event_time_taiwan.strftime("%Y-%m-%d %H:%M:%S")
    else:
        event_time_text = "未知時間"

    return (
        f"事件 ID：{event_id}\n"
        f"地點：{place}\n"
        f"規模：M {magnitude}\n"
        f"深度：{depth} km\n"
        f"座標：{latitude}, {longitude}\n"
        f"時間：{event_time_text}（台灣時間）\n"
        f"詳細資料：{detail_url}"
    )
def format_earthquake_message() -> str:

    try:
        earthquakes = fetch_earthquakes()

        if not earthquakes:
            return (
                "🌏 **地震狀態**\n"
                f"最近 {EARTHQUAKE_LOOKBACK_MINUTES} 分鐘內，"
                f"台灣附近 {SEARCH_RADIUS_KM} 公里內沒有查詢到地震。"
            )

        lines = [
            "🚨 **地震狀態：有地震！**",
            f"最近 {EARTHQUAKE_LOOKBACK_MINUTES} 分鐘內，"
            f"台灣附近 {SEARCH_RADIUS_KM} 公里內查詢到 {len(earthquakes)} 筆地震。\n"
        ]

        # 避免 Discord 訊息太長，最多顯示前 3 筆
        for index, event in enumerate(earthquakes[:3], start=1):
            lines.append(f"--- 第 {index} 筆 ---")
            lines.append(format_earthquake_event(event))

        if len(earthquakes) > 3:
            lines.append(f"\n其餘 {len(earthquakes) - 3} 筆地震未顯示，避免訊息過長。")

        return "\n".join(lines)

    except Exception as error:
        return (
            "🌏 **地震狀態**\n"
            f"取得地震資料失敗：{error}"
        )
# ============================================================
# 整合訊息
# ============================================================
def build_status_message() -> str:

    now_text = datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    earthquake_text = format_earthquake_message()
    weather_text = format_weather_message()

    message = (
        f"📢 **地震與台北天氣自動通知**\n"
        f"更新時間：{now_text}（台灣時間）\n\n"
        f"{earthquake_text}\n\n"
        f"{weather_text}"
    )

    return message
# ============================================================
# 主程式
# ============================================================
def main():
    print("地震與台北天氣 Discord 自動通知系統已啟動。")
    print(f"台北天氣地區：臺北市 {DISTRICT_NAME}")
    print(f"地震查詢範圍：台灣附近 {SEARCH_RADIUS_KM} 公里內")
    print(f"地震查詢時間：最近 {EARTHQUAKE_LOOKBACK_MINUTES} 分鐘")
    print(f"每次 GitHub Actions 執行會發送 {LOOP_COUNT} 次")
    print(f"每次間隔：{CHECK_INTERVAL_SECONDS} 秒")
    print("-" * 50)

    for count in range(1, LOOP_COUNT + 1):
        print(f"第 {count} / {LOOP_COUNT} 次檢查")

        message = build_status_message()

        print(message)
        print("-" * 50)

        push_to_discord(message)

        if count < LOOP_COUNT:
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()