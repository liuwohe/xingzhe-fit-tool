import logging

import requests

logger = logging.getLogger(__name__)


class OneLapClient:
    BASE_URL = "https://otm.onelap.cn"

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
            "Referer": "https://otm.onelap.cn/recordPage",
            "Origin": "https://otm.onelap.cn",
            "Accept": "application/json, text/plain, */*",
        })

    def _is_success(self, data: dict) -> bool:
        code = data.get("code")
        if code == 0 or code == 200 or data.get("success") is True:
            return True
        if code == 1 and "成功" in (data.get("msg") or ""):
            return True
        return False

    def test_connection(self) -> tuple[bool, str]:
        try:
            resp = self.session.post(
                f"{self.BASE_URL}/api/otm/ride_record/list",
                json={"page": 1, "limit": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                if self._is_success(data):
                    return True, "连接成功"
                return False, f"连接失败: {data.get('msg', '未知错误')} (code={data.get('code')})"
            if resp.status_code == 401:
                return False, "Token 无效或已过期，请重新获取"
            return False, f"连接失败: HTTP {resp.status_code}"
        except requests.RequestException as e:
            return False, f"网络错误: {e}"

    def upload_fit(self, file_path: str) -> tuple[bool, str]:
        try:
            import os
            filename = os.path.basename(file_path)

            with open(file_path, "rb") as f:
                files = {"jilu0": (filename, f, "application/octet-stream")}
                resp = self.session.post(
                    f"{self.BASE_URL}/api/otm/ride_record/upload/fit",
                    files=files,
                )

            if resp.status_code == 200:
                data = resp.json()
                if self._is_success(data):
                    return True, "上传成功"
                return False, f"{data.get('msg', '上传失败')} (code={data.get('code')})"
            if resp.status_code == 401:
                return False, "Token 无效或已过期"
            return False, f"上传失败: HTTP {resp.status_code}"

        except requests.RequestException as e:
            logger.error("上传 FIT 失败, file=%s: %s", file_path, e)
            return False, f"上传失败: {e}"
        except FileNotFoundError:
            return False, f"文件不存在: {file_path}"
