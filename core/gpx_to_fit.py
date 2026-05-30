import logging
from datetime import datetime, timezone

import gpxpy
from garmin_fit_sdk import Encoder

logger = logging.getLogger(__name__)

FIT_EPOCH_S = 631065600


def _to_semicircles(degrees: float) -> int:
    return int(degrees * (2**31 / 180))


def _to_fit_ts(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) - FIT_EPOCH_S


class GpxToFitConverter:
    def convert(self, gpx_path: str, fit_path: str, stream_data: dict = None) -> tuple[bool, str]:
        try:
            with open(gpx_path, "r", encoding="utf-8") as f:
                gpx = gpxpy.parse(f)
        except Exception as e:
            logger.error("解析 GPX 失败: %s", e)
            return False, f"解析 GPX 失败: {e}"

        trackpoints = []
        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    trackpoints.append(pt)

        if not trackpoints:
            return False, "GPX 文件中没有轨迹点"

        start_time = trackpoints[0].time or datetime.now(timezone.utc)
        end_time = trackpoints[-1].time or start_time

        # 从 stream_data 提取补充数据
        stream_hr = []
        stream_cad = []
        stream_pwr = []
        stream_elev = []
        if stream_data:
            stream_hr = stream_data.get("heartrate", []) or stream_data.get("heart_rate", [])
            stream_cad = stream_data.get("cadence", [])
            stream_pwr = stream_data.get("power", [])
            stream_elev = stream_data.get("elevation", []) or stream_data.get("altitude", [])

        try:
            encoder = Encoder()

            # file_id
            encoder.write_mesg({
                "mesg_num": 0,
                "type": 4,
                "manufacturer": 1,
                "product": 0,
                "time_created": _to_fit_ts(start_time),
            })

            # event: timer start
            encoder.write_mesg({
                "mesg_num": 21,
                "timestamp": _to_fit_ts(start_time),
                "event": 0,
                "event_type": 0,
            })

            # records
            for i, pt in enumerate(trackpoints):
                record = {"mesg_num": 20}
                if pt.time:
                    record["timestamp"] = _to_fit_ts(pt.time)
                if pt.latitude is not None and pt.longitude is not None:
                    record["position_lat"] = _to_semicircles(pt.latitude)
                    record["position_long"] = _to_semicircles(pt.longitude)
                if pt.elevation is not None:
                    record["altitude"] = pt.elevation
                elif i < len(stream_elev):
                    record["altitude"] = stream_elev[i]

                # GPX TrackPointExtension for hr/cadence/power
                has_hr = hasattr(pt, "heart_rate") and pt.heart_rate is not None
                has_cad = hasattr(pt, "cadence") and pt.cadence is not None
                has_pwr = hasattr(pt, "power") and pt.power is not None

                # 如果 GPX 没有，尝试从 stream 数据补充
                if not has_hr and i < len(stream_hr):
                    record["heart_rate"] = int(stream_hr[i])
                elif has_hr:
                    record["heart_rate"] = int(pt.heart_rate)

                if not has_cad and i < len(stream_cad):
                    record["cadence"] = int(stream_cad[i])
                elif has_cad:
                    record["cadence"] = int(pt.cadence)

                if not has_pwr and i < len(stream_pwr):
                    record["power"] = int(stream_pwr[i])
                elif has_pwr:
                    record["power"] = int(pt.power)

                encoder.write_mesg(record)

            # session
            total_elapsed = int((end_time - start_time).total_seconds())
            total_distance = 0
            for track in gpx.tracks:
                for segment in track.segments:
                    total_distance += int(segment.length_2d() or 0)

            encoder.write_mesg({
                "mesg_num": 18,
                "timestamp": _to_fit_ts(end_time),
                "event": 9,
                "event_type": 1,
                "start_time": _to_fit_ts(start_time),
                "sport": self._sport_type(gpx),
                "total_elapsed_time": total_elapsed * 1000,
                "total_timer_time": total_elapsed * 1000,
                "total_distance": total_distance,
                "total_calories": 0,
                "first_lap_index": 0,
                "num_laps": 1,
            })

            # lap
            encoder.write_mesg({
                "mesg_num": 19,
                "timestamp": _to_fit_ts(end_time),
                "event": 9,
                "event_type": 9,
                "start_time": _to_fit_ts(start_time),
                "total_elapsed_time": total_elapsed * 1000,
                "total_timer_time": total_elapsed * 1000,
                "total_distance": total_distance,
                "total_calories": 0,
            })

            # event: timer stop
            encoder.write_mesg({
                "mesg_num": 21,
                "timestamp": _to_fit_ts(end_time),
                "event": 0,
                "event_type": 1,
            })

            # activity
            encoder.write_mesg({
                "mesg_num": 34,
                "timestamp": _to_fit_ts(end_time),
                "total_timer_time": total_elapsed * 1000,
                "num_sessions": 1,
                "type": 0,
                "event": 26,
                "event_type": 1,
            })

            data = encoder.close()
            with open(fit_path, "wb") as f:
                f.write(data)

            return True, f"转换成功: {fit_path}"
        except Exception as e:
            logger.error("生成 FIT 失败: %s", e)
            return False, f"生成 FIT 失败: {e}"

    def _sport_type(self, gpx) -> int:
        for track in gpx.tracks:
            t = (track.type or "").lower()
            if "cycling" in t or "bike" in t or "骑行" in t:
                return 2
            if "running" in t or "run" in t or "跑步" in t:
                return 1
            if "hiking" in t or "徒步" in t:
                return 10
            if "walking" in t or "步行" in t:
                return 17
            if "swimming" in t or "swim" in t or "游泳" in t:
                return 5
        return 2  # default cycling