"""
飞书多维表格AI五子棋 - 主程序
"""

import json
import time
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from queue import Queue
from threading import Thread, Lock

from . import config
from .feishu_api import FeishuAPI
from .llm_parser import LLMParser, SimpleParser
from .ai_engine import GobangAI
from .visualizer import BattleVisualizer
from .ranking import ELORanking

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GobangManager:
    """五子棋管理器"""
    
    def __init__(self, use_llm: bool = True, llm_api_key: Optional[str] = None):
        """
        初始化管理器
        
        Args:
            use_llm: 是否使用LLM解析策略
            llm_api_key: LLM API Key
        """
        self.feishu = FeishuAPI()
        self.visualizer = BattleVisualizer()
        self.ranking = ELORanking()
        
        # 策略解析器
        if use_llm:
            self.parser = LLMParser(api_key=llm_api_key)
        else:
            self.parser = SimpleParser()
            
        # 多维表格信息
        self.wiki_token = config.FEISHU_WIKI_TOKEN
        self.app_token = config.FEISHU_APP_TOKEN
        
        # 表ID
        self.strategy_table_id = config.FEISHU_TABLE_IDS.get("strategy")
        self.battle_table_id = config.FEISHU_TABLE_IDS.get("battle")
        self.ranking_table_id = config.FEISHU_TABLE_IDS.get("ranking")
        
        # 已处理的策略ID
        self.processed_strategy_ids = set()
        
        # 任务队列
        self.task_queue = Queue()
        self.is_processing = False
        self.queue_lock = Lock()
        
    def initialize(self):
        """初始化多维表格结构"""
        logger.info("正在初始化...")
        
        # 获取bitable的app_token
        if not self.app_token:
            try:
                self.app_token = self.feishu.get_bitable_app_token(self.wiki_token)
                logger.info(f"获取到app_token: {self.app_token}")
            except Exception as e:
                logger.error(f"获取app_token失败: {e}")
                self.app_token = self.wiki_token
                
        # 确保截图目录存在
        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
        
        # 检查并创建数据表
        self._setup_tables()
        
        # 加载已有的排名数据
        self._load_ranking_data()
        
        logger.info("初始化完成")
        
    def _setup_tables(self):
        """设置数据表结构"""
        # 获取现有表列表
        try:
            tables = self.feishu.list_tables(self.app_token)
            existing_tables = {t.get("name"): t.get("table_id") for t in tables}
            logger.info(f"现有数据表: {existing_tables}")
        except Exception as e:
            logger.error(f"获取数据表列表失败: {e}")
            existing_tables = {}
            
        # 策略提交表字段定义
        strategy_fields = [
            {"field_name": "策略名称", "type": 1},  # 文本
            {"field_name": "自然语言策略", "type": 1},  # 文本
            {"field_name": "提交者", "type": 11},  # 人员
            {"field_name": "提交时间", "type": 5},  # 日期
            {"field_name": "状态", "type": 3, "property": {"options": [
                {"name": "待处理"},
                {"name": "解析中"},
                {"name": "对战中"},
                {"name": "已完成"},
                {"name": "失败"}
            ]}},  # 单选
            {"field_name": "解析后参数", "type": 1},  # 文本（JSON）
        ]
        
        # 对战记录表字段定义
        battle_fields = [
            {"field_name": "对战ID", "type": 1},  # 文本
            {"field_name": "策略名称", "type": 1},  # 文本
            {"field_name": "提交者", "type": 11},  # 人员
            {"field_name": "对战结果", "type": 3, "property": {"options": [
                {"name": "胜利"},
                {"name": "失败"},
                {"name": "平局"}
            ]}},  # 单选
            {"field_name": "总步数", "type": 2},  # 数字
            {"field_name": "对战时间", "type": 5},  # 日期
            {"field_name": "棋谱", "type": 1},  # 文本
            {"field_name": "对战截图", "type": 17},  # 附件
        ]
        
        # 排名表字段定义
        ranking_fields = [
            {"field_name": "策略名称", "type": 1},  # 文本
            {"field_name": "提交者", "type": 11},  # 人员
            {"field_name": "ELO积分", "type": 2},  # 数字
            {"field_name": "胜场", "type": 2},  # 数字
            {"field_name": "负场", "type": 2},  # 数字
            {"field_name": "平局", "type": 2},  # 数字
            {"field_name": "总场次", "type": 2},  # 数字
            {"field_name": "胜率", "type": 1},  # 文本
            {"field_name": "排名", "type": 2},  # 数字
            {"field_name": "最佳战绩", "type": 1},  # 文本
        ]
        
        # 处理策略提交表
        if "策略提交" in existing_tables:
            self.strategy_table_id = existing_tables["策略提交"]
            logger.info(f"使用现有策略提交表: {self.strategy_table_id}")
            self._ensure_fields(self.strategy_table_id, strategy_fields)
        elif "数据表" in existing_tables:
            # 将数据表作为策略提交表
            self.strategy_table_id = existing_tables["数据表"]
            logger.info(f"使用数据表作为策略提交表: {self.strategy_table_id}")
            self._ensure_fields(self.strategy_table_id, strategy_fields)
        else:
            try:
                self.strategy_table_id = self.feishu.create_table(
                    self.app_token, "策略提交", strategy_fields
                )
                logger.info(f"创建策略提交表: {self.strategy_table_id}")
            except Exception as e:
                logger.error(f"创建策略提交表失败: {e}")
                
        # 处理对战记录表
        if "对战记录" in existing_tables:
            self.battle_table_id = existing_tables["对战记录"]
            logger.info(f"使用现有对战记录表: {self.battle_table_id}")
            self._ensure_fields(self.battle_table_id, battle_fields)
        else:
            try:
                self.battle_table_id = self.feishu.create_table(
                    self.app_token, "对战记录", battle_fields
                )
                logger.info(f"创建对战记录表: {self.battle_table_id}")
            except Exception as e:
                logger.error(f"创建对战记录表失败: {e}")
                
        # 处理排名表
        if "排行榜" in existing_tables:
            self.ranking_table_id = existing_tables["排行榜"]
            logger.info(f"使用现有排行榜: {self.ranking_table_id}")
            self._ensure_fields(self.ranking_table_id, ranking_fields)
        elif "排名" in existing_tables:
            self.ranking_table_id = existing_tables["排名"]
            logger.info(f"使用现有排名表: {self.ranking_table_id}")
            self._ensure_fields(self.ranking_table_id, ranking_fields)
        else:
            try:
                self.ranking_table_id = self.feishu.create_table(
                    self.app_token, "排行榜", ranking_fields
                )
                logger.info(f"创建排行榜: {self.ranking_table_id}")
            except Exception as e:
                logger.error(f"创建排行榜失败: {e}")
                
    def _ensure_fields(self, table_id: str, required_fields: List[Dict[str, Any]]):
        """确保表包含所有必需的字段"""
        try:
            existing_fields = self.feishu.list_fields(self.app_token, table_id)
            existing_field_names = {f.get("field_name") for f in existing_fields}
            logger.info(f"表 {table_id} 现有字段: {existing_field_names}")
            
            for field_def in required_fields:
                field_name = field_def.get("field_name")
                if field_name not in existing_field_names:
                    logger.info(f"添加缺失字段: {field_name}")
                    try:
                        self.feishu.create_field(
                            self.app_token,
                            table_id,
                            field_name,
                            field_def.get("type"),
                            field_def.get("property")
                        )
                        logger.info(f"字段 {field_name} 添加成功")
                    except Exception as e:
                        logger.error(f"添加字段 {field_name} 失败: {e}")
                        
        except Exception as e:
            logger.error(f"检查字段失败: {e}")
            
    def _load_ranking_data(self):
        """加载排名数据"""
        if not self.ranking_table_id:
            return
            
        try:
            records = self.feishu.get_all_records(self.app_token, self.ranking_table_id)
            for record in records:
                fields = record.get("fields", {})
                # 尝试获取策略名称作为ID
                strategy_name = fields.get("策略名称")
                if strategy_name:
                    from .ranking import PlayerStats
                    # 确保数字字段是整数类型
                    elo_rating = self._safe_int(fields.get("ELO积分"), config.ELO_INITIAL)
                    wins = self._safe_int(fields.get("胜场"), 0)
                    losses = self._safe_int(fields.get("负场"), 0)
                    draws = self._safe_int(fields.get("平局"), 0)
                        
                    player = PlayerStats(
                        player_id=strategy_name,
                        elo_rating=elo_rating,
                        wins=wins,
                        losses=losses,
                        draws=draws
                    )
                    self.ranking.players[strategy_name] = player
            logger.info(f"加载了{len(self.ranking.players)}个玩家的排名数据")
        except Exception as e:
            logger.error(f"加载排名数据失败: {e}")
            
    def _safe_int(self, value, default: int = 0) -> int:
        """安全地将值转换为整数"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
            
    def poll_and_process(self):
        """轮询并处理新策略"""
        logger.info("开始轮询新策略...")
        logger.info(f"轮询间隔: {config.POLL_INTERVAL}秒")
        
        while True:
            try:
                self._check_and_process_strategies()
            except Exception as e:
                logger.error(f"处理策略时出错: {e}")
                
            time.sleep(config.POLL_INTERVAL)
            
    def _check_and_process_strategies(self):
        """检查并处理新策略"""
        if not self.strategy_table_id:
            logger.warning("策略表ID未设置")
            return
            
        try:
            records = self.feishu.get_all_records(self.app_token, self.strategy_table_id)
            
            for record in records:
                record_id = record.get("record_id")
                fields = record.get("fields", {})
                status = fields.get("状态")
                strategy_name = fields.get("策略名称", "未命名")
                
                # 跳过已处理的记录
                if record_id in self.processed_strategy_ids:
                    continue
                    
                # 只处理待处理的策略
                if status == "待处理":
                    logger.info(f"发现新策略: {strategy_name} (ID: {record_id})")
                    # 加入队列
                    self.task_queue.put((record_id, fields))
                    
            # 处理队列中的任务
            self._process_queue()
                    
        except Exception as e:
            logger.error(f"获取策略记录失败: {e}")
            
    def _process_queue(self):
        """处理任务队列"""
        with self.queue_lock:
            if self.is_processing:
                logger.info("正在处理其他任务，等待中...")
                return
                
            if self.task_queue.empty():
                return
                
            self.is_processing = True
            
        try:
            while not self.task_queue.empty():
                record_id, fields = self.task_queue.get()
                self._process_strategy(record_id, fields)
                # 短暂延迟，避免API限流
                time.sleep(1)
        finally:
            with self.queue_lock:
                self.is_processing = False
                
    def _process_strategy(self, record_id: str, fields: Dict[str, Any]):
        """处理单个策略"""
        strategy_name = fields.get("策略名称", "未命名")
        natural_strategy = fields.get("自然语言策略", "")
        
        # 获取提交者信息
        submitter = fields.get("提交者")
        submitter_name = "未知用户"
        if submitter and isinstance(submitter, list) and len(submitter) > 0:
            submitter_name = submitter[0].get("name", "未知用户")
            
        if not natural_strategy:
            logger.warning(f"策略 {strategy_name} 的自然语言策略为空")
            self._update_strategy_status(record_id, "失败")
            return
            
        try:
            # 更新状态为解析中
            self._update_strategy_status(record_id, "解析中")
            
            # 解析策略
            logger.info(f"正在解析策略: {strategy_name}")
            params = self.parser.parse_strategy(natural_strategy)
            
            # 保存解析结果
            self._update_strategy_params(record_id, params)
            
            # 更新状态为对战中
            self._update_strategy_status(record_id, "对战中")
            
            # 进行对战
            logger.info(f"开始对战: {strategy_name} (提交者: {submitter_name})")
            result, moves, screenshot_path, winning_line = self.visualizer.run_battle_with_visual(
                params, strategy_name, show_window=True, move_delay=300, result_delay=3000
            )
            
            # 记录对战结果
            battle_id = f"battle_{int(time.time())}"
            self._save_battle_record(
                battle_id=battle_id,
                strategy_name=strategy_name,
                submitter=submitter,
                result=result,
                moves=moves,
                screenshot_path=screenshot_path
            )
            
            # 更新排名
            self._update_ranking(strategy_name, submitter, result)
            
            # 更新状态为已完成
            self._update_strategy_status(record_id, "已完成")
            
            # 标记为已处理
            self.processed_strategy_ids.add(record_id)
            
            logger.info(f"策略 {strategy_name} 处理完成，结果: {result}")
            
        except Exception as e:
            logger.error(f"处理策略失败: {e}")
            self._update_strategy_status(record_id, "失败")
            
    def _update_strategy_status(self, record_id: str, status: str):
        """更新策略状态"""
        try:
            self.feishu.update_record(
                self.app_token, self.strategy_table_id,
                record_id, {"状态": status}
            )
        except Exception as e:
            logger.error(f"更新策略状态失败: {e}")
            
    def _update_strategy_params(self, record_id: str, params: Dict[str, Any]):
        """更新策略参数"""
        try:
            self.feishu.update_record(
                self.app_token, self.strategy_table_id,
                record_id, {"解析后参数": json.dumps(params, ensure_ascii=False)}
            )
        except Exception as e:
            logger.error(f"更新策略参数失败: {e}")
            
    def _save_battle_record(self, battle_id: str, strategy_name: str,
                           submitter: Any, result: str, 
                           moves: List[Tuple[int, int]], screenshot_path: str):
        """保存对战记录"""
        if not self.battle_table_id:
            return
            
        try:
            # 格式化棋谱
            moves_str = json.dumps(moves, ensure_ascii=False)
            
            # 准备记录数据
            fields = {
                "对战ID": battle_id,
                "策略名称": strategy_name,
                "对战结果": result,
                "总步数": len(moves),
                "对战时间": int(time.time() * 1000),  # 毫秒时间戳
                "棋谱": moves_str
            }
            
            # 如果有提交者信息
            if submitter:
                fields["提交者"] = submitter
                
            # 创建记录
            record_id = self.feishu.create_record(self.app_token, self.battle_table_id, fields)
            
            # 上传截图
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    self.feishu.upload_image(
                        self.app_token, self.battle_table_id,
                        record_id, "对战截图", screenshot_path
                    )
                    logger.info(f"截图上传成功: {screenshot_path}")
                except Exception as e:
                    logger.error(f"截图上传失败: {e}")
                    
            logger.info(f"对战记录保存成功: {battle_id}")
            
        except Exception as e:
            logger.error(f"保存对战记录失败: {e}")
            
    def _update_ranking(self, strategy_name: str, submitter: Any, result: str):
        """更新排名"""
        if not self.ranking_table_id:
            return
            
        try:
            # 获取或创建玩家
            player = self.ranking.get_player(strategy_name)
            
            # 更新积分
            if result == "胜利":
                # 胜利：与默认AI对战获胜，获得积分
                player.wins += 1
                # 根据当前积分计算获得的积分
                elo_change = max(10, 30 - (player.elo_rating - config.ELO_INITIAL) // 100)
                player.elo_rating += elo_change
            elif result == "失败":
                player.losses += 1
                # 失败扣分较少
                elo_change = max(5, 15 - (config.ELO_INITIAL - player.elo_rating) // 200)
                player.elo_rating = max(100, player.elo_rating - elo_change)
            else:  # 平局
                player.draws += 1
                # 平局积分变化很小
                player.elo_rating += 2
                
            # 更新排名表
            self._sync_ranking_table()
            
        except Exception as e:
            logger.error(f"更新排名失败: {e}")
            
    def _sync_ranking_table(self):
        """同步排名表"""
        try:
            # 获取现有记录
            existing_records = self.feishu.get_all_records(
                self.app_token, self.ranking_table_id
            )
            existing_map = {}
            for record in existing_records:
                name = record.get("fields", {}).get("策略名称")
                if name:
                    existing_map[name] = record.get("record_id")
                    
            # 获取排名列表
            ranking_list = self.ranking.get_ranking()
            
            for rank, player in enumerate(ranking_list, 1):
                # 计算胜率
                win_rate = f"{player.win_rate * 100:.1f}%"
                
                # 计算最佳战绩
                best_record = f"最高{player.elo_rating}分"
                
                data = {
                    "策略名称": player.player_id,
                    "ELO积分": player.elo_rating,
                    "胜场": player.wins,
                    "负场": player.losses,
                    "平局": player.draws,
                    "总场次": player.total_games,
                    "胜率": win_rate,
                    "排名": rank,
                    "最佳战绩": best_record
                }
                
                if player.player_id in existing_map:
                    # 更新现有记录
                    self.feishu.update_record(
                        self.app_token, self.ranking_table_id,
                        existing_map[player.player_id], data
                    )
                else:
                    # 创建新记录
                    self.feishu.create_record(
                        self.app_token, self.ranking_table_id, data
                    )
                    
            logger.info("排名表更新完成")
            
        except Exception as e:
            logger.error(f"同步排名表失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="飞书多维表格AI五子棋")
    parser.add_argument("--no-llm", action="store_true", help="不使用LLM，使用关键词匹配解析策略")
    parser.add_argument("--api-key", type=str, help="LLM API Key")
    parser.add_argument("--poll-interval", type=int, default=10, help="轮询间隔（秒）")
    
    args = parser.parse_args()
    
    # 更新轮询间隔
    if args.poll_interval:
        config.POLL_INTERVAL = args.poll_interval
        
    # 创建管理器
    manager = GobangManager(
        use_llm=not args.no_llm,
        llm_api_key=args.api_key
    )
    
    # 初始化
    manager.initialize()
    
    # 轮询模式
    manager.poll_and_process()


if __name__ == "__main__":
    main()
