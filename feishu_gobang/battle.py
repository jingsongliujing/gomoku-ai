"""
对战引擎模块
负责AI之间的对战
"""

from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

from .ai_engine import GobangAI


class BattleResult(Enum):
    """对战结果"""
    RED_WIN = "红方胜"
    BLUE_WIN = "蓝方胜"
    DRAW = "平局"
    RED_TIMEOUT = "红方超时"
    BLUE_TIMEOUT = "蓝方超时"
    ERROR = "异常"


@dataclass
class MoveRecord:
    """落子记录"""
    step: int              # 步数
    stone_type: int        # 棋子类型 1=白, 2=黑
    position: Tuple[int, int]  # 位置
    value: int = 0         # 评估分值（可选）


@dataclass
class BattleRecord:
    """对战记录"""
    battle_id: str                      # 对战ID
    red_strategy_id: str                # 红方策略ID
    blue_strategy_id: str               # 蓝方策略ID
    red_params: Dict[str, Any]          # 红方参数
    blue_params: Dict[str, Any]         # 蓝方参数
    result: BattleResult                # 对战结果
    winner_id: Optional[str]            # 获胜方ID
    total_moves: int                    # 总步数
    moves: List[MoveRecord]             # 落子记录
    duration_seconds: float             # 对战时长（秒）


class BattleEngine:
    """对战引擎"""
    
    def __init__(self, max_moves: int = 225):
        """
        初始化对战引擎
        
        Args:
            max_moves: 最大步数（15x15棋盘最多225步）
        """
        self.max_moves = max_moves
        
    def battle(self, 
               red_params: Dict[str, Any],
               blue_params: Dict[str, Any],
               red_id: str = "red",
               blue_id: str = "blue") -> BattleRecord:
        """
        执行一场对战
        
        Args:
            red_params: 红方AI参数
            blue_params: 蓝方AI参数
            red_id: 红方策略ID
            blue_id: 蓝方策略ID
            
        Returns:
            对战记录
        """
        import time
        import uuid
        
        start_time = time.time()
        battle_id = str(uuid.uuid4())[:8]
        
        # 创建两个AI实例
        # 红方执黑(2)先手，蓝方执白(1)后手
        red_ai = GobangAI(red_params)
        blue_ai = GobangAI(blue_params)
        
        # 共享棋盘状态（使用红方的棋盘作为主棋盘）
        main_board = red_ai
        
        moves = []
        step = 0
        current_stone = 2  # 黑棋先手
        
        result = BattleResult.DRAW
        winner_id = None
        
        while step < self.max_moves:
            step += 1
            
            # 选择当前AI
            if current_stone == 2:  # 黑棋 = 红方
                current_ai = red_ai
                current_id = red_id
            else:  # 白棋 = 蓝方
                current_ai = blue_ai
                current_id = blue_id
                
            # 同步棋盘状态
            current_ai.board = main_board.board.copy()
            current_ai.move_history = main_board.move_history.copy()
            
            # 获取AI落子
            try:
                move_pos = current_ai.get_best_move(current_stone)
            except Exception as e:
                print(f"AI计算异常: {e}")
                if current_stone == 2:
                    result = BattleResult.RED_TIMEOUT
                    winner_id = blue_id
                else:
                    result = BattleResult.BLUE_TIMEOUT
                    winner_id = red_id
                break
                
            if move_pos is None:
                # 没有空位，平局
                result = BattleResult.DRAW
                break
                
            # 记录落子
            record = MoveRecord(
                step=step,
                stone_type=current_stone,
                position=move_pos
            )
            moves.append(record)
            
            # 在主棋盘落子
            main_board.place_stone(move_pos, current_stone)
            
            # 检查是否获胜
            if main_board.check_win(move_pos, current_stone):
                if current_stone == 2:
                    result = BattleResult.RED_WIN
                    winner_id = red_id
                else:
                    result = BattleResult.BLUE_WIN
                    winner_id = blue_id
                break
                
            # 检查是否平局
            if main_board.is_board_full():
                result = BattleResult.DRAW
                break
                
            # 切换棋子
            current_stone = 1 if current_stone == 2 else 2
            
        end_time = time.time()
        
        return BattleRecord(
            battle_id=battle_id,
            red_strategy_id=red_id,
            blue_strategy_id=blue_id,
            red_params=red_params,
            blue_params=blue_params,
            result=result,
            winner_id=winner_id,
            total_moves=step,
            moves=moves,
            duration_seconds=end_time - start_time
        )
        
    def battle_best_of_n(self,
                         red_params: Dict[str, Any],
                         blue_params: Dict[str, Any],
                         n: int = 3,
                         red_id: str = "red",
                         blue_id: str = "blue") -> Tuple[str, List[BattleRecord]]:
        """
        N局M胜制对战
        
        Args:
            red_params: 红方参数
            blue_params: 蓝方参数
            n: 对战局数（奇数）
            red_id: 红方ID
            blue_id: 蓝方ID
            
        Returns:
            (获胜方ID, 所有对战记录列表)
        """
        wins_needed = (n // 2) + 1
        red_wins = 0
        blue_wins = 0
        records = []
        
        for i in range(n):
            # 交替先后手
            if i % 2 == 0:
                record = self.battle(red_params, blue_params, red_id, blue_id)
            else:
                # 交换红蓝方
                record = self.battle(blue_params, red_params, blue_id, red_id)
                # 调整结果中的红蓝方标识
                if record.result == BattleResult.RED_WIN:
                    record.result = BattleResult.BLUE_WIN
                    record.winner_id = blue_id
                elif record.result == BattleResult.BLUE_WIN:
                    record.result = BattleResult.RED_WIN
                    record.winner_id = red_id
                    
            records.append(record)
            
            if record.winner_id == red_id:
                red_wins += 1
            elif record.winner_id == blue_id:
                blue_wins += 1
                
            if red_wins >= wins_needed:
                return red_id, records
            if blue_wins >= wins_needed:
                return blue_id, records
                
        # 所有局数完成，比较胜场
        if red_wins > blue_wins:
            return red_id, records
        elif blue_wins > red_wins:
            return blue_id, records
        else:
            return "draw", records
            
    def format_battle_summary(self, record: BattleRecord) -> str:
        """格式化对战摘要"""
        summary = f"对战ID: {record.battle_id}\n"
        summary += f"红方: {record.red_strategy_id}\n"
        summary += f"蓝方: {record.blue_strategy_id}\n"
        summary += f"结果: {record.result.value}\n"
        summary += f"获胜方: {record.winner_id or '无'}\n"
        summary += f"总步数: {record.total_moves}\n"
        summary += f"对战时长: {record.duration_seconds:.2f}秒\n"
        
        # 格式化棋谱
        summary += "\n棋谱:\n"
        for move in record.moves:
            stone = "黑" if move.stone_type == 2 else "白"
            grid_x = (move.position[0] - 28) // 40
            grid_y = (move.position[1] - 28) // 40
            summary += f"第{move.step}步: {stone} ({grid_x}, {grid_y})\n"
            
        return summary
        
    def record_to_dict(self, record: BattleRecord) -> Dict[str, Any]:
        """将对战记录转换为字典（用于存储到多维表格）"""
        moves_data = []
        for move in record.moves:
            grid_x = (move.position[0] - 28) // 40
            grid_y = (move.position[1] - 28) // 40
            moves_data.append({
                "step": move.step,
                "stone": move.stone_type,
                "x": grid_x,
                "y": grid_y
            })
            
        return {
            "battle_id": record.battle_id,
            "red_strategy_id": record.red_strategy_id,
            "blue_strategy_id": record.blue_strategy_id,
            "result": record.result.value,
            "winner_id": record.winner_id,
            "total_moves": record.total_moves,
            "moves": moves_data,
            "duration_seconds": round(record.duration_seconds, 2)
        }
