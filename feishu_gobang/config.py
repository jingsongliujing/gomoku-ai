"""
飞书多维表格AI五子棋 - 配置文件
从.env文件加载敏感配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件（项目根目录）
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# 飞书应用配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# 多维表格配置
FEISHU_WIKI_TOKEN = os.getenv("FEISHU_WIKI_TOKEN", "")
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "")

# 表ID配置
FEISHU_TABLE_IDS = {
    "strategy": os.getenv("FEISHU_STRATEGY_TABLE_ID", ""),
    "battle": os.getenv("FEISHU_BATTLE_TABLE_ID", ""),
    "ranking": os.getenv("FEISHU_RANKING_TABLE_ID", "")
}

# 飞书API地址
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# LLM配置
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# 轮询配置
POLL_INTERVAL = 10  # 轮询间隔（秒）

# 对战配置
BATTLE_ROUNDS = 3           # 每组对战场次（3局2胜）

# ELO积分配置
ELO_INITIAL = 1500          # 初始积分
ELO_K_FACTOR = 32           # K因子

# 棋盘配置
BOARD_SIZE = 15             # 棋盘大小 15x15
CELL_SIZE = 40              # 格点间距
BOARD_START = 28            # 起始坐标

# 窗口配置
WINDOW_WIDTH = 615
WINDOW_HEIGHT = 650  # 稍微增加高度用于显示信息

# 截图配置
SCREENSHOT_DIR = "screenshots"  # 截图保存目录

# 默认AI权重（防守型，让玩家更有挑战性）
DEFAULT_ATTACK_WEIGHTS = {
    "live_four": 40000,
    "dead_four": 30000,
    "live_three": 20000,
    "dead_three": 15000,
    "live_two": 1000,
    "dead_two": 500,
    "single": 30
}

DEFAULT_DEFENSE_WEIGHTS = {
    "live_four": 42000,
    "dead_four": 32000,
    "live_three": 22000,
    "dead_three": 17000,
    "live_two": 1200,
    "dead_two": 600,
    "single": 40
}

DEFAULT_AI_PARAMS = {
    "style": "balanced",
    "attack_weights": DEFAULT_ATTACK_WEIGHTS.copy(),
    "defense_weights": DEFAULT_DEFENSE_WEIGHTS.copy(),
    "attack_bias": 1.0,
    "defense_bias": 1.1,
    "center_preference": 1.2,
    "opening_strategy": "center"
}
