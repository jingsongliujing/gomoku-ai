"""
AI引擎模块
支持动态权重参数的五子棋AI
"""

from typing import Dict, Any, Optional, Tuple, List
from . import config


class GobangAI:
    """五子棋AI引擎"""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化AI引擎
        
        Args:
            params: AI参数字典，包含attack_weights, defense_weights等
        """
        self.board_size = config.BOARD_SIZE
        self.cell_size = 40  # 格点间距
        self.start_pos = 28  # 起始坐标
        self.board = {}      # 棋盘状态
        self.move_history = []  # 落子历史
        
        # 设置参数
        if params is None:
            params = self._get_default_params()
        self.params = params
        
        # 提取权重
        self.attack_weights = params.get("attack_weights", config.DEFAULT_ATTACK_WEIGHTS)
        self.defense_weights = params.get("defense_weights", config.DEFAULT_DEFENSE_WEIGHTS)
        self.attack_bias = params.get("attack_bias", 1.0)
        self.defense_bias = params.get("defense_bias", 1.0)
        self.center_preference = params.get("center_preference", 1.0)
        self.opening_strategy = params.get("opening_strategy", "center")
        
        self._init_board()
        
    def _get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            "style": "balanced",
            "attack_weights": config.DEFAULT_ATTACK_WEIGHTS.copy(),
            "defense_weights": config.DEFAULT_DEFENSE_WEIGHTS.copy(),
            "attack_bias": 1.0,
            "defense_bias": 1.0,
            "center_preference": 1.0,
            "opening_strategy": "center"
        }
        
    def _init_board(self):
        """初始化棋盘"""
        self.board = {}
        for i in range(self.board_size):
            for j in range(self.board_size):
                x = self.start_pos + i * self.cell_size
                y = self.start_pos + j * self.cell_size
                self.board[f"{x}|{y}"] = 0
        self.move_history = []
        
    def reset(self):
        """重置棋盘"""
        self._init_board()
        
    def _pos_to_key(self, pos: Tuple[int, int]) -> str:
        """坐标转字符串key"""
        return f"{pos[0]}|{pos[1]}"
        
    def _key_to_pos(self, key: str) -> Tuple[int, int]:
        """字符串key转坐标"""
        x, y = key.split("|")
        return (int(x), int(y))
        
    def _is_valid_pos(self, x: int, y: int) -> bool:
        """检查坐标是否有效"""
        min_pos = self.start_pos
        max_pos = self.start_pos + (self.board_size - 1) * self.cell_size
        return min_pos <= x <= max_pos and min_pos <= y <= max_pos
        
    def _get_grid_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """将像素坐标转换为网格坐标 (0-14)"""
        x = (pos[0] - self.start_pos) // self.cell_size
        y = (pos[1] - self.start_pos) // self.cell_size
        return (x, y)
        
    def is_empty(self, pos: Tuple[int, int]) -> bool:
        """检查位置是否为空"""
        key = self._pos_to_key(pos)
        return self.board.get(key, 0) == 0
        
    def place_stone(self, pos: Tuple[int, int], stone_type: int) -> bool:
        """
        落子
        
        Args:
            pos: 像素坐标 (x, y)
            stone_type: 棋子类型 1=白棋, 2=黑棋
            
        Returns:
            是否成功
        """
        key = self._pos_to_key(pos)
        if key in self.board and self.board[key] == 0:
            self.board[key] = stone_type
            self.move_history.append((pos, stone_type))
            return True
        return False
        
    def _get_point(self, pos: Tuple[int, int], direction: int, offset: int) -> int:
        """
        获取指定方向偏移位置的棋子状态
        
        Args:
            pos: 当前位置
            direction: 方向 (1-8)
            offset: 偏移量
            
        Returns:
            0=空, 1=白棋, 2=黑棋, 5=边界外
        """
        # 8个方向：右、右下、下、左下、左、左上、上、右上
        directions = [
            [0, 1], [1, 1], [1, 0], [1, -1],
            [0, -1], [-1, -1], [-1, 0], [-1, 1]
        ]
        
        x, y = pos
        dx, dy = directions[direction - 1]
        new_x = x + dx * offset * self.cell_size
        new_y = y + dy * offset * self.cell_size
        
        if not self._is_valid_pos(new_x, new_y):
            return 5
            
        return self.board.get(f"{new_x}|{new_y}", 0)
        
    def _point_value(self, pos: Tuple[int, int], identify1: int, identify2: int,
                    weights: Dict[str, int]) -> int:
        """
        计算某位置的价值分数
        
        Args:
            pos: 位置
            identify1: 己方标识
            identify2: 对方标识
            weights: 权重配置
            
        Returns:
            分值
        """
        value = 0
        
        for i in range(1, 9):  # 8个方向
            # 活四: *1111_
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == identify1 and
                self._get_point(pos, i, 5) == 0):
                value += weights.get("live_four", 40000)
                
            # 死四1: *11112
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == identify1 and
                self._get_point(pos, i, 5) == identify2):
                value += weights.get("dead_four", 30000)
                
            # 死四2: 1*111
            if (self._get_point(pos, i, -1) == identify1 and
                self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1):
                value += weights.get("dead_four", 30000)
                
            # 死四3: 11*11
            if (self._get_point(pos, i, -2) == identify1 and
                self._get_point(pos, i, -1) == identify1 and
                self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1):
                value += weights.get("dead_four", 30000)
                
            # 活三1: *111_
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == 0):
                value += weights.get("live_three", 20000)
                
            # 活三2: *1_11_
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == 0 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == identify1 and
                self._get_point(pos, i, 5) == 0):
                value += weights.get("live_three", 20000)
                
            # 死三1: *1112
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == identify2):
                value += weights.get("dead_three", 15000)
                
            # 死三2: _1_112
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == 0 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == identify1 and
                self._get_point(pos, i, 5) == identify2):
                value += weights.get("dead_three", 15000)
                
            # 死三3: _11_12
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == 0 and
                self._get_point(pos, i, 4) == identify1 and
                self._get_point(pos, i, 5) == identify2):
                value += weights.get("dead_three", 15000)
                
            # 死三4: 1__11
            if (self._get_point(pos, i, -1) == identify1 and
                self._get_point(pos, i, 1) == 0 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1):
                value += weights.get("dead_three", 15000)
                
            # 死三5: 1_1_1
            if (self._get_point(pos, i, -1) == identify1 and
                self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == 0 and
                self._get_point(pos, i, 3) == identify1):
                value += weights.get("dead_three", 15000)
                
            # 死三6: 2_111_2
            if (self._get_point(pos, i, -1) == identify2 and
                self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == 0 and
                self._get_point(pos, i, 5) == identify2):
                value += weights.get("dead_three", 15000)
                
            # 活二1: __11__
            if (self._get_point(pos, i, -1) == 0 and
                self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == identify1 and
                self._get_point(pos, i, 3) == 0 and
                self._get_point(pos, i, 4) == 0):
                value += weights.get("live_two", 1000)
                
            # 活二2: _1_1_
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == 0 and
                self._get_point(pos, i, 3) == identify1 and
                self._get_point(pos, i, 4) == 0):
                value += weights.get("live_two", 1000)
                
            # 单子+两空: *1__
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == 0 and
                self._get_point(pos, i, 3) == 0):
                value += weights.get("single", 30)
                
            # 单子+一空: *1_
            if (self._get_point(pos, i, 1) == identify1 and
                self._get_point(pos, i, 2) == 0):
                value += weights.get("single", 20)
                
            # 单子: *1
            if self._get_point(pos, i, 1) == identify1:
                value += weights.get("single", 10)
                
        return value
        
    def _calculate_center_bonus(self, pos: Tuple[int, int]) -> float:
        """计算中心位置加分"""
        grid_x, grid_y = self._get_grid_pos(pos)
        center = (self.board_size - 1) / 2
        distance = ((grid_x - center) ** 2 + (grid_y - center) ** 2) ** 0.5
        max_distance = (center ** 2 + center ** 2) ** 0.5
        
        # 距离中心越近，加分越高
        bonus = 1.0 + (self.center_preference - 1.0) * (1.0 - distance / max_distance)
        return bonus
        
    def get_best_move(self, stone_type: int) -> Optional[Tuple[int, int]]:
        """
        获取AI的最佳落子位置
        
        Args:
            stone_type: AI的棋子类型 1=白棋, 2=黑棋
            
        Returns:
            最佳位置的像素坐标，如果没有空位返回None
        """
        opponent_type = 2 if stone_type == 1 else 1
        
        # 开局策略
        if not self.move_history:
            return self._get_opening_move()
            
        # 检查是否有空位
        empty_positions = []
        for key, value in self.board.items():
            if value == 0:
                empty_positions.append(self._key_to_pos(key))
                
        if not empty_positions:
            return None
            
        best_pos = None
        max_attack = 0
        max_defense = 0
        best_attack_pos = None
        best_defense_pos = None
        
        for pos in empty_positions:
            # 计算进攻分值
            attack_value = self._point_value(pos, stone_type, opponent_type, self.attack_weights)
            attack_value *= self.attack_bias
            attack_value *= self._calculate_center_bonus(pos)
            
            # 计算防守分值
            defense_value = self._point_value(pos, opponent_type, stone_type, self.defense_weights)
            defense_value *= self.defense_bias
            
            if attack_value > max_attack:
                max_attack = attack_value
                best_attack_pos = pos
                
            if defense_value > max_defense:
                max_defense = defense_value
                best_defense_pos = pos
                
        # 决策：进攻优先还是防守优先
        if max_attack >= max_defense:
            return best_attack_pos
        else:
            return best_defense_pos
            
    def _get_opening_move(self) -> Tuple[int, int]:
        """获取开局落子"""
        center = self.start_pos + (self.board_size // 2) * self.cell_size
        
        if self.opening_strategy == "center":
            return (center, center)
        elif self.opening_strategy == "corner":
            # 选择靠近中心的角落
            offset = self.cell_size * 2
            return (center - offset, center - offset)
        else:  # random
            import random
            offset = self.cell_size * random.randint(-2, 2)
            return (center + offset, center + offset)
            
    def check_win(self, pos: Tuple[int, int], stone_type: int) -> bool:
        """
        检查是否获胜
        
        Args:
            pos: 最后落子位置
            stone_type: 棋子类型
            
        Returns:
            是否五子连线
        """
        # 检查4个方向：水平、垂直、主对角线、副对角线
        directions = [
            [(0, 1), (0, -1)],   # 水平
            [(1, 0), (-1, 0)],   # 垂直
            [(1, 1), (-1, -1)],  # 主对角线
            [(1, -1), (-1, 1)]   # 副对角线
        ]
        
        for dir_pair in directions:
            count = 1  # 包含当前子
            
            for dx, dy in dir_pair:
                for i in range(1, 5):
                    x = pos[0] + dx * i * self.cell_size
                    y = pos[1] + dy * i * self.cell_size
                    
                    if not self._is_valid_pos(x, y):
                        break
                        
                    key = f"{x}|{y}"
                    if self.board.get(key) == stone_type:
                        count += 1
                    else:
                        break
                        
            if count >= 5:
                return True
                
        return False
        
    def is_board_full(self) -> bool:
        """检查棋盘是否已满"""
        return all(v != 0 for v in self.board.values())
        
    def get_board_state(self) -> Dict[str, int]:
        """获取棋盘状态副本"""
        return self.board.copy()
        
    def get_move_history(self) -> List[Tuple[Tuple[int, int], int]]:
        """获取落子历史"""
        return self.move_history.copy()
        
    def get_params(self) -> Dict[str, Any]:
        """获取AI参数"""
        return self.params.copy()
