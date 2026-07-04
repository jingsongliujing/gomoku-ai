"""
ELO排名计算模块
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from . import config


@dataclass
class PlayerStats:
    """玩家统计数据"""
    player_id: str
    elo_rating: int = config.ELO_INITIAL
    wins: int = 0
    losses: int = 0
    draws: int = 0
    
    @property
    def total_games(self) -> int:
        return self.wins + self.losses + self.draws
        
    @property
    def win_rate(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games


class ELORanking:
    """ELO等级分排名系统"""
    
    def __init__(self, k_factor: int = config.ELO_K_FACTOR, 
                 initial_rating: int = config.ELO_INITIAL):
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.players: Dict[str, PlayerStats] = {}
        
    def get_player(self, player_id: str) -> PlayerStats:
        """获取或创建玩家"""
        if player_id not in self.players:
            self.players[player_id] = PlayerStats(
                player_id=player_id,
                elo_rating=self.initial_rating
            )
        return self.players[player_id]
        
    def _expected_score(self, rating_a: int, rating_b: int) -> float:
        """
        计算预期得分
        
        Args:
            rating_a: 玩家A的积分
            rating_b: 玩家B的积分
            
        Returns:
            玩家A的预期得分 (0-1)
        """
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))
        
    def update_ratings(self, winner_id: str, loser_id: str, is_draw: bool = False):
        """
        更新积分
        
        Args:
            winner_id: 获胜方ID
            loser_id: 失败方ID
            is_draw: 是否平局
        """
        winner = self.get_player(winner_id)
        loser = self.get_player(loser_id)
        
        # 计算预期得分
        expected_winner = self._expected_score(winner.elo_rating, loser.elo_rating)
        expected_loser = self._expected_score(loser.elo_rating, winner.elo_rating)
        
        if is_draw:
            # 平局
            actual_winner = 0.5
            actual_loser = 0.5
            winner.draws += 1
            loser.draws += 1
        else:
            # 有胜负
            actual_winner = 1.0
            actual_loser = 0.0
            winner.wins += 1
            loser.losses += 1
            
        # 更新积分
        winner.elo_rating += int(self.k_factor * (actual_winner - expected_winner))
        loser.elo_rating += int(self.k_factor * (actual_loser - expected_loser))
        
        # 积分不能低于0
        winner.elo_rating = max(0, winner.elo_rating)
        loser.elo_rating = max(0, loser.elo_rating)
        
    def update_from_battle(self, red_id: str, blue_id: str, 
                          winner_id: Optional[str]):
        """
        从对战结果更新积分
        
        Args:
            red_id: 红方ID
            blue_id: 蓝方ID
            winner_id: 获胜方ID（None表示平局）
        """
        if winner_id is None:
            self.update_ratings(red_id, blue_id, is_draw=True)
        elif winner_id == red_id:
            self.update_ratings(red_id, blue_id, is_draw=False)
        elif winner_id == blue_id:
            self.update_ratings(blue_id, red_id, is_draw=False)
            
    def get_ranking(self) -> list:
        """
        获取排名列表
        
        Returns:
            按积分排序的玩家列表
        """
        players = list(self.players.values())
        players.sort(key=lambda p: p.elo_rating, reverse=True)
        return players
        
    def get_rank(self, player_id: str) -> int:
        """
        获取玩家排名
        
        Args:
            player_id: 玩家ID
            
        Returns:
            排名（从1开始）
        """
        ranking = self.get_ranking()
        for i, player in enumerate(ranking):
            if player.player_id == player_id:
                return i + 1
        return -1
        
    def player_to_dict(self, player: PlayerStats) -> Dict[str, Any]:
        """将玩家数据转换为字典（用于存储到多维表格）"""
        return {
            "player_id": player.player_id,
            "elo_rating": player.elo_rating,
            "wins": player.wins,
            "losses": player.losses,
            "draws": player.draws,
            "total_games": player.total_games,
            "win_rate": round(player.win_rate * 100, 2),
            "rank": self.get_rank(player.player_id)
        }
        
    def dict_to_player(self, data: Dict[str, Any]) -> PlayerStats:
        """从字典恢复玩家数据"""
        player = PlayerStats(
            player_id=data["player_id"],
            elo_rating=data.get("elo_rating", self.initial_rating),
            wins=data.get("wins", 0),
            losses=data.get("losses", 0),
            draws=data.get("draws", 0)
        )
        return player
        
    def save_state(self) -> Dict[str, Any]:
        """保存状态"""
        return {
            "k_factor": self.k_factor,
            "initial_rating": self.initial_rating,
            "players": {
                pid: self.player_to_dict(p) 
                for pid, p in self.players.items()
            }
        }
        
    def load_state(self, state: Dict[str, Any]):
        """加载状态"""
        self.k_factor = state.get("k_factor", config.ELO_K_FACTOR)
        self.initial_rating = state.get("initial_rating", config.ELO_INITIAL)
        
        for pid, pdata in state.get("players", {}).items():
            self.players[pid] = self.dict_to_player(pdata)
