import logging
import os
import time
from datetime import datetime, timezone

import requests

from core.models import FileType, SportType, WorkoutInfo

logger = logging.getLogger(__name__)

SPORT_MAP = {
    1: SportType.RUNNING,
    2: SportType.HIKING,
    3: SportType.CYCLING,
    4: SportType.WALKING,
    5: SportType.SWIMMING,
}


class RateLimitError(Exception):
    pass


class XingzheClient:
    BASE_URL = "https://www.imxingzhe.com/api/v1"

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.imxingzhe.com/xingzhe/workouts/list",
        })

    def test_connection(self) -> tuple[bool, str]:
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/pgworkout/",
                params={"page": 1, "page_size": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return True, "连接成功"
                return False, data.get("msg", "连接失败")
            if resp.status_code == 401:
                return False, "Token 无效或已过期，请重新获取"
            return False, f"连接失败: HTTP {resp.status_code}"
        except requests.RequestException as e:
            return False, f"网络错误: {e}"

    def get_workout_list(self, offset: int = 0, limit: int = 16) -> list[WorkoutInfo]:
        resp = self.session.get(
            f"{self.BASE_URL}/pgworkout/",
            params={"offset": offset, "limit": limit},
        )
        if resp.status_code == 400:
            data = resp.json()
            msg = data.get("msg", "")
            if "limit exceeded" in msg:
                raise RateLimitError(msg)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"API 返回错误: {data.get('msg', '未知错误')}")

        inner = data.get("data", {})
        results = inner.get("data", []) if isinstance(inner, dict) else []

        workouts = []
        for item in results:
            if isinstance(item, dict):
                workouts.append(self._parse_workout(item))
        return workouts

    def get_all_workouts(self, progress_callback=None) -> list[WorkoutInfo]:
        all_workouts = []
        offset = 0
        limit = 16

        while True:
            for retry in range(3):
                try:
                    workouts = self.get_workout_list(offset, limit)
                    break
                except RateLimitError as e:
                    wait = 2 * (retry + 1)
                    logger.warning("请求限流, 等待 %ds 后重试: %s", wait, e)
                    time.sleep(wait)
                except requests.RequestException:
                    raise
            else:
                workouts = []

            if not workouts:
                break
            all_workouts.extend(workouts)
            if progress_callback:
                progress_callback(len(all_workouts), 0)
            if len(workouts) < limit:
                break
            offset += limit
            time.sleep(1)
        return all_workouts

    def _parse_workout(self, item: dict) -> WorkoutInfo:
        workout_id = item.get("id", 0)
        title = item.get("title", "") or f"运动 {workout_id}"
        sport_code = item.get("sport", 0)
        sport_type = SPORT_MAP.get(sport_code, SportType.OTHER)
        distance = float(item.get("distance", 0) or 0) / 1000
        duration = int(item.get("duration", 0) or 0)

        start_ts = item.get("start_time", 0)
        date = None
        if start_ts:
            try:
                date = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                pass

        has_hr = item.get("has_heartrate", False)
        has_cad = item.get("has_cadence", False)
        has_pwr = item.get("has_power", False)
        is_fit = item.get("is_fit", False)

        if is_fit:
            file_type = FileType.FIT
        else:
            file_type = FileType.GPX

        return WorkoutInfo(
            id=workout_id,
            title=title,
            date=date,
            distance_km=distance,
            duration_seconds=duration,
            sport_type=sport_type,
            file_type=file_type,
            file_url="",
            avg_speed=float(item.get("avg_speed", 0) or 0),
        )

    def get_workout_detail(self, workout_id: int) -> dict:
        resp = self.session.get(f"{self.BASE_URL}/pgworkout/{workout_id}/")
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") in (0, 200):
            return data.get("data", {}).get("workout", {})
        raise RuntimeError(f"获取详情失败: {data.get('msg', '未知错误')}")

    def get_workout_stream(self, workout_id: int) -> dict:
        """获取运动原始轨迹流数据（含心率、踏频、功率等）"""
        resp = self.session.get(f"{self.BASE_URL}/pgworkout/{workout_id}/stream/")
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") in (0, 200):
            return data.get("data", {})
        return {}

    def download_fit(self, workout_id: int, save_path: str) -> tuple[bool, str]:
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/workout/{workout_id}/fit/",
                stream=True,
            )
            if resp.status_code == 404:
                return False, "FIT文件不存在"
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "")
            if "json" in ct or "html" in ct:
                return False, "FIT文件不存在"
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, save_path
        except requests.RequestException as e:
            logger.error("下载 FIT 失败, workout_id=%s: %s", workout_id, e)
            return False, f"下载FIT失败: {e}"

    def download_gpx(self, workout_id: int, save_path: str) -> tuple[bool, str]:
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/pgworkout/{workout_id}/gpx",
                stream=True,
            )
            resp.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, save_path
        except requests.RequestException as e:
            logger.error("下载 GPX 失败, workout_id=%s: %s", workout_id, e)
            return False, f"下载GPX失败: {e}"

    def download_workout(self, workout: WorkoutInfo, save_dir: str,
                         convert_gpx: bool = True) -> tuple[bool, str, FileType]:
        date_prefix = workout.date.strftime("%Y%m%d") if workout.date else str(workout.id)
        safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in workout.title)[:50]
        base_name = f"{date_prefix}_{safe_title}"

        # 优先尝试直接下载 FIT 文件
        fit_path = os.path.join(save_dir, f"{base_name}.fit")
        ok, msg = self.download_fit(workout.id, fit_path)
        if ok:
            logger.info("直接下载 FIT 成功, workout_id=%s", workout.id)
            return True, msg, FileType.FIT
        logger.info("FIT 直接下载不可用, workout_id=%s, 原因: %s, 尝试 GPX 转换", workout.id, msg)

        # 回退: 下载 GPX 再转 FIT
        gpx_path = os.path.join(save_dir, f"{base_name}.gpx")
        ok, msg = self.download_gpx(workout.id, gpx_path)
        if not ok:
            return ok, msg, FileType.UNKNOWN

        if convert_gpx:
            from core.gpx_to_fit import GpxToFitConverter
            stream = self._try_get_stream(workout.id)
            converter = GpxToFitConverter()
            ok2, msg2 = converter.convert(gpx_path, fit_path, stream_data=stream)
            if ok2:
                os.remove(gpx_path)
                return True, msg2, FileType.FIT
            return True, f"GPX 已下载 (FIT转换失败: {msg2})", FileType.GPX

        return True, gpx_path, FileType.GPX

    def _try_get_stream(self, workout_id: int) -> dict:
        try:
            return self.get_workout_stream(workout_id)
        except Exception as e:
            logger.warning("获取 stream 数据失败, workout_id=%s: %s", workout_id, e)
            return {}