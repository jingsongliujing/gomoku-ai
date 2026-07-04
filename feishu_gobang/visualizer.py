"""
五子棋对战可视化模块
支持实时可视化对战过程
"""

import os
import pygame
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime

from . import config
from .ai_engine import GobangAI


class BattleVisualizer:
    """对战可视化器"""
    
    def __init__(self):
        """初始化可视化器"""
        # 颜色定义
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.BROWN = (210, 180, 140)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 100, 255)
        self.GREEN = (0, 180, 0)
        self.GRAY = (128, 128, 128)
        self.YELLOW = (255, 255, 0)
        self.LIGHT_RED = (255, 200, 200)
        self.LIGHT_GREEN = (200, 255, 200)
        
        # 确保截图目录存在
        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
        
    def run_battle_with_visual(self, 
                               user_params: Dict[str, Any],
                               user_name: str = "用户策略",
                               show_window: bool = True,
                               move_delay: int = 300,
                               result_delay: int = 3000) -> Tuple[str, List[Tuple[int, int]], str, List[Tuple[int, int]]]:
        """
        运行对战并可视化
        
        Args:
            user_params: 用户策略参数
            user_name: 用户名称
            show_window: 是否显示窗口
            move_delay: 每步延迟（毫秒）
            result_delay: 结果显示延迟（毫秒）
            
        Returns:
            (结果, 棋谱, 截图路径, 获胜连线坐标列表)
        """
        # 初始化Pygame
        pygame.init()
        
        if show_window:
            screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            pygame.display.set_caption(f"AI五子棋对战 - {user_name} VS 默认AI")
        else:
            # 不显示窗口，使用离屏渲染
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            
        # 加载字体
        try:
            font = pygame.font.Font("gobang_client/font/12345.TTF", 28)
            small_font = pygame.font.Font("gobang_client/font/12345.TTF", 18)
            tiny_font = pygame.font.Font("gobang_client/font/12345.TTF", 14)
        except:
            font = pygame.font.SysFont("microsoftyahei", 28)
            small_font = pygame.font.SysFont("microsoftyahei", 18)
            tiny_font = pygame.font.SysFont("microsoftyahei", 14)
            
        # 创建AI实例
        user_ai = GobangAI(user_params)
        default_ai = GobangAI(config.DEFAULT_AI_PARAMS)
        
        # 对战记录
        moves = []
        winning_line = []  # 获胜连线
        
        # 用户执黑(2)先手，默认AI执白(1)后手
        current_stone = 2
        result = "进行中"
        last_move = None
        
        # 绘制初始棋盘
        self._draw_board(screen, font, small_font, tiny_font, 
                        user_name, "默认AI", moves, result, last_move, winning_line)
        
        # 进行对战
        max_moves = 225  # 15x15
        step = 0
        
        running = True
        while running and step < max_moves:
            # 处理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                    
            if not running:
                break
                
            step += 1
            
            # 选择当前AI
            if current_stone == 2:
                current_ai = user_ai
            else:
                current_ai = default_ai
                
            # 同步棋盘状态
            current_ai.board = user_ai.board.copy()
            current_ai.move_history = user_ai.move_history.copy()
            
            # 获取AI落子
            move_pos = current_ai.get_best_move(current_stone)
            
            if move_pos is None:
                result = "平局"
                break
                
            # 记录落子
            grid_x = (move_pos[0] - config.BOARD_START) // config.CELL_SIZE
            grid_y = (move_pos[1] - config.BOARD_START) // config.CELL_SIZE
            moves.append((grid_x, grid_y))
            last_move = (grid_x, grid_y)
            
            # 在两个AI的棋盘上落子
            user_ai.place_stone(move_pos, current_stone)
            default_ai.board = user_ai.board.copy()
            default_ai.move_history = user_ai.move_history.copy()
            
            # 绘制当前状态
            status_text = f"第{step}步 - {'黑棋' if current_stone == 2 else '白棋'}落子"
            self._draw_board(screen, font, small_font, tiny_font,
                           user_name, "默认AI", moves, status_text, last_move, winning_line)
            
            # 检查是否获胜
            if user_ai.check_win(move_pos, current_stone):
                winning_line = self._find_winning_line(user_ai, move_pos, current_stone)
                if current_stone == 2:
                    result = "胜利"
                else:
                    result = "失败"
                break
                
            # 切换棋子
            current_stone = 1 if current_stone == 2 else 2
            
            # 延迟
            if show_window:
                pygame.time.delay(move_delay)
                
        # 绘制最终结果
        result_color = self.GREEN if "胜" in result else (self.RED if "败" in result else self.YELLOW)
        result_text = f"{'★' if '胜' in result else '☆'} {result} {'★' if '胜' in result else '☆'}"
        self._draw_board(screen, font, small_font, tiny_font,
                        user_name, "默认AI", moves, result_text, last_move, winning_line, 
                        result_color=result_color, show_result=True)
        
        # 保存截图
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(config.SCREENSHOT_DIR, f"battle_{timestamp}.png")
        pygame.image.save(screen, screenshot_path)
        
        # 显示结果一段时间
        if show_window:
            # 等待用户关闭窗口或超时
            wait_start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - wait_start < result_delay:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        wait_start = 0  # 立即退出
                        break
                pygame.time.delay(100)
                
        pygame.quit()
        
        return result, moves, screenshot_path, winning_line
        
    def _find_winning_line(self, ai: GobangAI, last_move: Tuple[int, int], stone_type: int) -> List[Tuple[int, int]]:
        """找到获胜的五子连线"""
        cell_size = config.CELL_SIZE
        start = config.BOARD_START
        
        # 转换为网格坐标
        gx = (last_move[0] - start) // cell_size
        gy = (last_move[1] - start) // cell_size
        
        # 四个方向：水平、垂直、主对角线、副对角线
        directions = [
            [(0, 1), (0, -1)],   # 水平
            [(1, 0), (-1, 0)],   # 垂直
            [(1, 1), (-1, -1)],  # 主对角线
            [(1, -1), (-1, 1)]   # 副对角线
        ]
        
        for dir_pair in directions:
            line = [(gx, gy)]
            
            for dx, dy in dir_pair:
                for i in range(1, 5):
                    nx, ny = gx + dx * i, gy + dy * i
                    if 0 <= nx < config.BOARD_SIZE and 0 <= ny < config.BOARD_SIZE:
                        pos = (start + nx * cell_size, start + ny * cell_size)
                        key = f"{pos[0]}|{pos[1]}"
                        if ai.board.get(key) == stone_type:
                            line.append((nx, ny))
                        else:
                            break
                    else:
                        break
                        
            if len(line) >= 5:
                # 取前5个或全部
                return line[:5] if len(line) == 5 else line
                
        return []
        
    def _draw_board(self, screen, font, small_font, tiny_font,
                   red_name: str, blue_name: str, 
                   moves: List[Tuple[int, int]], status: str,
                   last_move: Optional[Tuple[int, int]] = None,
                   winning_line: List[Tuple[int, int]] = None,
                   result_color: Tuple[int, int, int] = None,
                   show_result: bool = False):
        """绘制棋盘"""
        # 清屏
        screen.fill(self.BROWN)
        
        # 绘制标题区域
        title_bg = pygame.Rect(0, 0, config.WINDOW_WIDTH, 50)
        pygame.draw.rect(screen, (60, 60, 60), title_bg)
        
        # 绘制标题
        title_text = font.render(f"{red_name} VS {blue_name}", True, self.WHITE)
        screen.blit(title_text, (config.WINDOW_WIDTH // 2 - title_text.get_width() // 2, 10))
        
        # 绘制状态
        status_color = result_color if result_color else self.BLACK
        status_text = small_font.render(f"状态: {status}", True, status_color)
        screen.blit(status_text, (10, 55))
        
        # 绘制步数
        step_text = small_font.render(f"步数: {len(moves)}", True, self.BLACK)
        screen.blit(step_text, (config.WINDOW_WIDTH - 120, 55))
        
        # 绘制棋盘背景
        board_rect = pygame.Rect(
            config.BOARD_START - 20,
            config.BOARD_START - 20 + 50,
            (config.BOARD_SIZE - 1) * config.CELL_SIZE + 40,
            (config.BOARD_SIZE - 1) * config.CELL_SIZE + 40
        )
        pygame.draw.rect(screen, (220, 190, 150), board_rect)
        
        # 绘制棋盘网格
        board_offset_y = 50  # 标题偏移
        for i in range(config.BOARD_SIZE):
            # 横线
            y = config.BOARD_START + i * config.CELL_SIZE + board_offset_y
            pygame.draw.line(screen, self.BLACK, 
                           (config.BOARD_START, y), 
                           (config.BOARD_START + (config.BOARD_SIZE - 1) * config.CELL_SIZE, y), 1)
            # 竖线
            x = config.BOARD_START + i * config.CELL_SIZE
            pygame.draw.line(screen, self.BLACK, 
                           (x, config.BOARD_START + board_offset_y), 
                           (x, config.BOARD_START + (config.BOARD_SIZE - 1) * config.CELL_SIZE + board_offset_y), 1)
                           
        # 绘制天元和星位
        star_points = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]
        for gx, gy in star_points:
            x = config.BOARD_START + gx * config.CELL_SIZE
            y = config.BOARD_START + gy * config.CELL_SIZE + board_offset_y
            pygame.draw.circle(screen, self.BLACK, (x, y), 4)
            
        # 标记获胜连线
        if winning_line and show_result:
            for gx, gy in winning_line:
                x = config.BOARD_START + gx * config.CELL_SIZE
                y = config.BOARD_START + gy * config.CELL_SIZE + board_offset_y
                # 绘制黄色高亮圆圈
                pygame.draw.circle(screen, self.YELLOW, (x, y), 20, 3)
                
        # 绘制棋子
        for i, (gx, gy) in enumerate(moves):
            x = config.BOARD_START + gx * config.CELL_SIZE
            y = config.BOARD_START + gy * config.CELL_SIZE + board_offset_y
            
            is_last = (gx, gy) == last_move
            is_winning = winning_line and (gx, gy) in winning_line and show_result
            
            if i % 2 == 0:  # 黑棋
                pygame.draw.circle(screen, self.BLACK, (x, y), 16)
                # 显示步号（只显示前50步）
                if i < 50:
                    num_text = tiny_font.render(str(i + 1), True, self.WHITE)
                    screen.blit(num_text, (x - num_text.get_width() // 2, y - num_text.get_height() // 2))
            else:  # 白棋
                pygame.draw.circle(screen, self.WHITE, (x, y), 16)
                pygame.draw.circle(screen, self.BLACK, (x, y), 16, 1)  # 边框
                # 显示步号（只显示前50步）
                if i < 50:
                    num_text = tiny_font.render(str(i + 1), True, self.BLACK)
                    screen.blit(num_text, (x - num_text.get_width() // 2, y - num_text.get_height() // 2))
                    
            # 标记最后一步
            if is_last:
                pygame.draw.circle(screen, self.RED, (x, y), 5)
                
            # 标记获胜棋子
            if is_winning:
                pygame.draw.circle(screen, self.YELLOW, (x, y), 20, 3)
                
        # 绘制图例
        legend_y = config.WINDOW_HEIGHT - 40
        
        # 黑棋图例
        pygame.draw.circle(screen, self.BLACK, (30, legend_y), 12)
        black_text = tiny_font.render(f"= {red_name} (先手)", True, self.BLACK)
        screen.blit(black_text, (45, legend_y - 7))
        
        # 白棋图例
        pygame.draw.circle(screen, self.WHITE, (220, legend_y), 12)
        pygame.draw.circle(screen, self.BLACK, (220, legend_y), 12, 1)
        white_text = tiny_font.render(f"= {blue_name} (后手)", True, self.BLACK)
        screen.blit(white_text, (235, legend_y - 7))
        
        # 最后一步标记图例
        pygame.draw.circle(screen, self.RED, (420, legend_y), 5)
        last_text = tiny_font.render("= 最后一步", True, self.BLACK)
        screen.blit(last_text, (430, legend_y - 7))
        
        # 更新显示
        pygame.display.flip()
        
    def generate_screenshot_from_moves(self, 
                                      moves: List[Tuple[int, int]],
                                      user_name: str,
                                      result: str,
                                      winning_line: List[Tuple[int, int]] = None) -> str:
        """
        根据已有棋谱生成截图（不进行对战）
        
        Args:
            moves: 棋谱
            user_name: 用户名称
            result: 对战结果
            winning_line: 获胜连线
            
        Returns:
            截图路径
        """
        pygame.init()
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        
        try:
            font = pygame.font.Font("gobang_client/font/12345.TTF", 28)
            small_font = pygame.font.Font("gobang_client/font/12345.TTF", 18)
            tiny_font = pygame.font.Font("gobang_client/font/12345.TTF", 14)
        except:
            font = pygame.font.SysFont("microsoftyahei", 28)
            small_font = pygame.font.SysFont("microsoftyahei", 18)
            tiny_font = pygame.font.SysFont("microsoftyahei", 14)
            
        last_move = moves[-1] if moves else None
        
        result_color = self.GREEN if "胜" in result else (self.RED if "败" in result else self.YELLOW)
        self._draw_board(screen, font, small_font, tiny_font,
                        user_name, "默认AI", moves, result, last_move, 
                        winning_line or [], result_color=result_color, show_result=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(config.SCREENSHOT_DIR, f"battle_{timestamp}.png")
        pygame.image.save(screen, screenshot_path)
        
        pygame.quit()
        
        return screenshot_path
