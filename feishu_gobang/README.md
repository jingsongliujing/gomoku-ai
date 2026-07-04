# 飞书多维表格AI五子棋

## 简介

这是一个基于飞书多维表格的AI五子棋游戏系统。用户可以在飞书多维表格中提交自然语言策略，系统会自动解析策略并与其他策略进行对战，最终在多维表格中显示排名。

## 功能特点

1. **自然语言策略**：用户可以用自然语言描述自己的下棋策略，如"我是一个激进型选手，优先攻击..."
2. **自动解析**：系统使用LLM（大语言模型）将自然语言转换为AI参数
3. **自动对战**：新策略会自动与排名前5的策略进行对战
4. **ELO排名**：使用ELO等级分系统计算排名
5. **多维表格集成**：所有数据都存储在飞书多维表格中

## 项目结构

```
feishu_gobang/
├── __init__.py          # 包初始化
├── config.py            # 配置文件
├── feishu_api.py        # 飞书API模块
├── llm_parser.py        # LLM策略解析模块
├── ai_engine.py         # AI引擎（支持动态参数）
├── battle.py            # 对战引擎
├── ranking.py           # ELO排名计算
├── main.py              # 主程序入口
└── requirements.txt     # 依赖列表
```

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置LLM API Key：
   - 编辑 `config.py` 中的 `LLM_API_KEY`
   - 或者在运行时通过 `--api-key` 参数传入

## 飞书多维表格配置

### 1. 创建多维表格

在飞书中创建一个多维表格，包含以下表：

#### 策略表（Strategy）
| 字段名 | 类型 | 说明 |
|--------|------|------|
| 策略名称 | 文本 | 用户自定义名称 |
| 自然语言策略 | 文本 | 用户输入的策略描述 |
| 解析后参数 | 文本 | LLM解析后的JSON参数 |
| 状态 | 单选 | 待解析/已解析/解析失败/对战中/已完成 |
| 创建时间 | 日期 | 自动记录 |

#### 对战记录表（Battle）
系统会自动创建此表。

#### 排名表（Ranking）
系统会自动创建此表。

### 2. 配置应用

1. 在飞书开放平台创建应用
2. 获取 App ID 和 App Secret
3. 更新 `config.py` 中的配置：
```python
FEISHU_APP_ID = "your_app_id"
FEISHU_APP_SECRET = "your_app_secret"
FEISHU_WIKI_TOKEN = "your_wiki_token"
```

### 3. 权限配置

应用需要以下权限：
- `bitable:app` - 多维表格应用权限
- `wiki:wiki:readonly` - 知识库只读权限

## 运行

### 轮询模式（推荐）

持续监听新策略并自动处理：
```bash
python -m feishu_gobang.main
```

### 指定参数运行

```bash
# 使用自定义API Key
python -m feishu_gobang.main --api-key "your-api-key"

# 不使用LLM，使用关键词匹配
python -m feishu_gobang.main --no-llm

# 自定义轮询间隔（秒）
python -m feishu_gobang.main --poll-interval 60
```

### 手动对战

手动触发两个策略之间的对战：
```bash
python -m feishu_gobang.main --manual-battle "策略ID1" "策略ID2"
```

## 策略示例

用户可以在飞书多维表格的"自然语言策略"字段中输入类似：

```
我是一个激进型选手，优先攻击，喜欢构建活三和活四。
开局喜欢占据中心位置。
防守时优先堵对方的活三。
遇到活四和死四时必须进攻。
```

系统会解析为：
```json
{
    "style": "aggressive",
    "attack_weights": {
        "live_four": 45000,
        "dead_four": 35000,
        "live_three": 25000,
        "dead_three": 18000,
        "live_two": 1500
    },
    "defense_weights": {
        "live_four": 40000,
        "dead_four": 30000,
        "live_three": 22000,
        "dead_three": 16000,
        "live_two": 1200
    },
    "attack_bias": 1.3,
    "defense_bias": 0.8,
    "center_preference": 1.5,
    "opening_strategy": "center"
}
```

## 排名系统

- 使用ELO等级分系统
- 初始积分：1500
- K因子：32
- 胜利：根据对手积分差获得积分
- 失败：根据对手积分差失去积分
- 平局：积分变化较小

## 注意事项

1. 确保飞书应用有足够的权限访问多维表格
2. LLM API Key需要有效（如果不使用 `--no-llm` 模式）
3. 对战会在后台进行，不会显示Pygame界面
4. 所有对战记录都会保存到多维表格中

## 许可证

本项目基于原python-gobang项目，使用GPLv3许可证。
