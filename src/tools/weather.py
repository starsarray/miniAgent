import json
import urllib.parse
import urllib.request
from typing import Any

from ..tool_registry import Tool


CITY_ALIASES = {
    "西安": "Xi'an",
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "成都": "Chengdu",
}


def run(arguments: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    city = str(arguments.get("city", "")).strip()
    if not city:
        raise ValueError("city 不能为空")

    query_city = CITY_ALIASES.get(city, city)
    encoded_city = urllib.parse.quote(query_city)
    url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"

    with urllib.request.urlopen(url, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    current = data["current_condition"][0]
    desc = _weather_desc(current)
    temp = current.get("temp_C")
    feels_like = current.get("FeelsLikeC")
    humidity = current.get("humidity")
    wind = current.get("windspeedKmph")

    answer = f"{city}当前天气：{desc}，气温 {temp}°C，体感 {feels_like}°C，湿度 {humidity}%，风速 {wind} km/h。"
    return {
        "tool": "weather",
        "success": True,
        "result": {
            "city": city,
            "description": desc,
            "temp_C": temp,
            "feels_like_C": feels_like,
            "humidity": humidity,
            "wind_kmph": wind,
            "answer": answer,
        },
        "error": None,
    }


def _weather_desc(current: dict[str, Any]) -> str:
    zh = current.get("lang_zh") or []
    if zh:
        return zh[0].get("value", "")
    desc = current.get("weatherDesc") or []
    if desc:
        return desc[0].get("value", "")
    return "未知"


def weather_tool() -> Tool:
    return Tool(
        name="weather",
        description="查询指定城市当前天气；用户问天气时调用此工具，不要调用 search。",
        parameters={"city": "string, required, 城市名，例如 '西安'"},
        func=run,
    )
