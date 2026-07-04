"""
LLM策略解析模块
将自然语言策略转换为AI参数
"""

import json
import requests
from typing import Dict, Any, Optional

from . import config


class LLMParser:
    """LLM策略解析器"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.LLM_API_KEY
        self.api_base = api_base or config.LLM_API_BASE
        self.model = model or config.LLM_MODEL
        
    def parse_strategy(self, natural_language_strategy: str) -> Dict[str, Any]:
        """
        将自然语言策略解析为AI参数
        
        Args:
            natural_language_strategy: 用户输入的自然语言策略
            
        Returns:
            解析后的AI参数字典
        """
        prompt = self._build_prompt(natural_language_strategy)
        
        try:
            response = self._call_llm(prompt)
            params = self._parse_response(response)
            params = self._validate_params(params)
            return params
        except Exception as e:
            print(f"LLM解析失败: {e}")
            return self._get_default_params()
            
    def _build_prompt(self, strategy: str) -> str:
        """构建提示词"""
        return f"""你是一个五子棋AI策略解析专家。请将用户的自然语言策略描述转换为AI的权重参数。

## 五子棋棋型说明

以下是五子棋中的关键棋型及其默认分值：

### 进攻棋型（我方棋子形成的威胁）
- **活四 (live_four)**: 四子相连且两端为空，如 `_XXXX_`，必胜态势，默认40000分
- **死四 (dead_four)**: 四子相连但一端被堵，如 `XXXXO` 或 `X_XXX`，默认30000分
- **活三 (live_three)**: 三子相连且两端为空，如 `_XXX_`，可发展为活四，默认20000分
- **死三 (dead_three)**: 三子相连但一端被堵，如 `XXXO` 或 `X_XX`，默认15000分
- **活二 (live_two)**: 两子相连且两端为空，如 `_XX_`，默认1000分
- **死二 (dead_two)**: 两子相连但一端被堵，如 `XXO`，默认500分
- **单子 (single)**: 单独一子，有扩展空间，默认30分

### 防守权重（对方棋子形成的威胁，需要防守）
防守权重与进攻类似，但通常略低于进攻（因为进攻优先）

### 策略风格参数
- **attack_bias**: 进攻倾向，1.0为平衡，>1.0更激进，<1.0更保守
- **defense_bias**: 防守倾向，1.0为平衡，>1.0更注重防守
- **center_preference**: 中心位置偏好，1.0为无偏好，>1.0更喜欢中心
- **opening_strategy**: 开局策略，可选值: "center"(中心开局), "corner"(角落开局), "random"(随机)

## 用户策略描述

{strategy}

## 输出要求

请输出严格的JSON格式，包含以下字段：

```json
{{
    "style": "aggressive/balanced/defensive",
    "attack_weights": {{
        "live_four": <数值>,
        "dead_four": <数值>,
        "live_three": <数值>,
        "dead_three": <数值>,
        "live_two": <数值>,
        "dead_two": <数值>,
        "single": <数值>
    }},
    "defense_weights": {{
        "live_four": <数值>,
        "dead_four": <数值>,
        "live_three": <数值>,
        "dead_three": <数值>,
        "live_two": <数值>,
        "dead_two": <数值>,
        "single": <数值>
    }},
    "attack_bias": <数值，0.5到2.0之间>,
    "defense_bias": <数值，0.5到2.0之间>,
    "center_preference": <数值，0.5到3.0之间>,
    "opening_strategy": "center/corner/random"
}}
```

注意：
1. 分值必须是正整数
2. 活四 > 死四 > 活三 > 死三 > 活二 > 死二 > 单子（分值递减）
3. 根据用户的策略风格调整各棋型的分值权重
4. 只输出JSON，不要有其他内容"""

    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个五子棋AI策略解析专家，只输出JSON格式的参数。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        if "error" in data:
            raise Exception(f"LLM API错误: {data['error'].get('message', '未知错误')}")
            
        return data["choices"][0]["message"]["content"]
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的JSON"""
        # 尝试提取JSON（可能被包裹在```json ... ```中）
        json_str = response.strip()
        if json_str.startswith("```"):
            # 提取代码块中的JSON
            lines = json_str.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_json = not in_json
                    continue
                if in_json:
                    json_lines.append(line)
            json_str = "\n".join(json_lines)
            
        return json.loads(json_str)
        
    def _validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证并修正参数"""
        default = self._get_default_params()
        
        # 确保所有必要的字段存在
        for key in default:
            if key not in params:
                params[key] = default[key]
                
        # 验证权重递减关系
        for weight_key in ["attack_weights", "defense_weights"]:
            weights = params.get(weight_key, {})
            default_weights = default[weight_key]
            
            for key in default_weights:
                if key not in weights:
                    weights[key] = default_weights[key]
                    
            # 确保分值递减
            order = ["live_four", "dead_four", "live_three", "dead_three", "live_two", "dead_two", "single"]
            for i in range(len(order) - 1):
                if weights[order[i]] < weights[order[i + 1]]:
                    weights[order[i]] = weights[order[i + 1]] * 2
                    
            params[weight_key] = weights
            
        # 验证范围
        params["attack_bias"] = max(0.5, min(2.0, params.get("attack_bias", 1.0)))
        params["defense_bias"] = max(0.5, min(2.0, params.get("defense_bias", 1.0)))
        params["center_preference"] = max(0.5, min(3.0, params.get("center_preference", 1.0)))
        
        if params.get("opening_strategy") not in ["center", "corner", "random"]:
            params["opening_strategy"] = "center"
            
        if params.get("style") not in ["aggressive", "balanced", "defensive"]:
            params["style"] = "balanced"
            
        return params
        
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


class SimpleParser:
    """
    简单的关键词匹配解析器（作为LLM的备用方案）
    当LLM不可用时使用
    """
    
    # 关键词映射
    KEYWORDS = {
        "aggressive": ["激进", "攻击", "进攻", "主动", "强势", "aggressive", "attack"],
        "defensive": ["防守", "防御", "保守", "稳健", "defensive", "defense"],
        "balanced": ["平衡", "均衡", "中庸", "balanced", "balance"],
        "center": ["中心", "中间", "中央", "center", "middle"],
        "corner": ["角落", "边角", "corner", "edge"],
    }
    
    def parse_strategy(self, natural_language_strategy: str) -> Dict[str, Any]:
        """解析策略（关键词匹配）"""
        strategy_lower = natural_language_strategy.lower()
        
        # 检测风格
        style = "balanced"
        for s, keywords in self.KEYWORDS.items():
            if s in ["aggressive", "defensive", "balanced"]:
                for kw in keywords:
                    if kw in strategy_lower:
                        style = s
                        break
                        
        # 检测开局
        opening = "center"
        for kw in self.KEYWORDS["corner"]:
            if kw in strategy_lower:
                opening = "corner"
                break
                
        # 根据风格调整参数
        params = self._get_default_params()
        params["style"] = style
        params["opening_strategy"] = opening
        
        if style == "aggressive":
            params["attack_bias"] = 1.3
            params["defense_bias"] = 0.8
            params["attack_weights"]["live_three"] = 25000
            params["attack_weights"]["dead_three"] = 18000
        elif style == "defensive":
            params["attack_bias"] = 0.8
            params["defense_bias"] = 1.3
            params["defense_weights"]["live_three"] = 22000
            params["defense_weights"]["dead_three"] = 16000
            
        # 检测特殊偏好
        for kw in ["活四", "live_four"]:
            if kw in strategy_lower:
                if style == "aggressive":
                    params["attack_weights"]["live_four"] = 50000
                else:
                    params["defense_weights"]["live_four"] = 45000
                    
        for kw in ["活三", "live_three"]:
            if kw in strategy_lower:
                if style == "aggressive":
                    params["attack_weights"]["live_three"] = 28000
                else:
                    params["defense_weights"]["live_three"] = 25000
                    
        return params
        
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
