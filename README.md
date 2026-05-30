# FitTool - 行者运动数据导出 & 顽鹿导入工具

将行者（imxingzhe.com）的运动数据导出为 FIT/GPX 文件，并支持一键导入到顽鹿（otm.onelap.cn）平台。

## 功能特性

- **行者数据导出**：获取全部运动记录，支持 FIT 直接下载，GPX 自动转换为 FIT
- **顽鹿数据导入**：批量上传 FIT 文件到顽鹿平台
- **自动同步**：填写两个平台 Token 后，一键完成 行者 → 顽鹿 的数据迁移
- **数据增强**：利用行者 Stream API 补充心率、踏频、功率等传感器数据
- **暗色主题**：Catppuccin Mocha 风格 UI

## 界面说明

### 自动同步（推荐）

填写行者 Token 和顽鹿 Token，分别测试连接成功后，点击"开始自动同步"即可一键完成数据迁移。

流程：行者获取运动列表 → 逐条下载 FIT/GPX → GPX 自动转 FIT → 上传到顽鹿 → 清理临时文件

### 行者导出

1. 输入行者 Token → 点击"连接测试"
2. 点击"获取运动列表"获取全部运动记录
3. 勾选需要导出的记录，选择保存目录
4. 点击"导出选中记录"

### 顽鹿导入

1. 输入顽鹿 Token → 点击"连接测试"
2. 添加 FIT 文件（支持选择文件或目录）
3. 点击"上传选中文件到顽鹿"

### 设置

保存行者/顽鹿 Token 和默认导出目录，下次启动自动填充。

## Token 获取方式

### 行者 Token

1. 浏览器登录 [行者官网](https://www.imxingzhe.com)
2. 按 F12 打开开发者工具
3. 通过部分查询请求头获取或者切换到 **Application** → **Local Storage** → `imxingzhe.com`
4. 找到并复制 `Token` 值，不带Bearer

### 顽鹿 Token

1. 浏览器登录 [顽鹿官网](https://otm.onelap.cn)
2. 按 F12 打开开发者工具
3. 通过请求头获取或者切换到 **Application** → **Local Storage** → `otm.onelap.cn`
4. 找到并复制 Token 值

> 注意：Token 有效期有限，过期后需重新获取。

## 从源码运行

### 环境要求

- Python 3.10+
- pip

### 安装依赖

```bash
pip install requests gpxpy garmin-fit-sdk PySide6
```

### 运行

```bash
python main.py
```

### 打包 EXE

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --name "FitTool" --add-data "ui/styles.py;ui" --hidden-import=core --hidden-import=core.models --hidden-import=core.xingzhe_client --hidden-import=core.onelap_client --hidden-import=core.gpx_to_fit --hidden-import=ui --hidden-import=ui.main_window --hidden-import=ui.xingzhe_tab --hidden-import=ui.onelap_tab --hidden-import=ui.settings_tab --hidden-import=ui.auto_sync_tab --hidden-import=ui.styles --hidden-import=gpxpy --hidden-import=garmin_fit_sdk --hidden-import=requests main.py
```

打包产物位于 `dist/FitTool/FitTool.exe`。

## 项目结构

```
fittool/
├── main.py                 # 入口
├── core/
│   ├── models.py           # 数据模型（SportType, WorkoutInfo 等）
│   ├── xingzhe_client.py   # 行者 API 客户端
│   ├── onelap_client.py    # 顽鹿 API 客户端
│   └── gpx_to_fit.py       # GPX → FIT 转换器
├── ui/
│   ├── main_window.py      # 主窗口
│   ├── auto_sync_tab.py    # 自动同步页签
│   ├── xingzhe_tab.py      # 行者导出页签
│   ├── onelap_tab.py       # 顽鹿导入页签
│   ├── settings_tab.py     # 设置页签
│   └── styles.py           # 暗色主题样式
└── config.json             # 用户配置（Token、目录，自动生成）
```

## 技术说明

- **行者 API**：使用 `offset/limit` 分页获取运动列表，优先通过 `/workout/{id}/fit/` 直接下载 FIT 文件，不可用时回退到 GPX 下载 + 转换
- **GPX 转 FIT**：基于 `garmin-fit-sdk` 构建 FIT 文件，包含 file_id、record、session、lap、activity 等消息；通过 Stream API 补充心率/踏频/功率数据
- **顽鹿上传**：POST multipart/form-data，字段名 `jilu0`，Authorization 直接使用 Token（无 Bearer 前缀）
