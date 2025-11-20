import requests
import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

class DeepSeekClient:
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
    def recognize_intent(self, user_input: str, candidate_intents: List[str]) -> str:
        """意图识别"""
        prompt = f"""
        请分析用户输入并分类到以下意图之一：
        可选意图：{', '.join(candidate_intents)}
        
        用户输入："{user_input}"
        
        请只返回意图名称，不要其他任何内容。
        如果没有匹配的意图，请返回 "unknown"。
        """
        
        return self._call_api(prompt, temperature=0.1)
    
    def generate_reply(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """生成智能回复"""
        system_prompt = """
        你是智慧医院的专业客服助手，请提供专业、友好的回复。
        注意：你只能提供健康建议和医疗科普，不能进行诊断或开处方。
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史
        if context and 'conversation_history' in context:
            for msg in context['conversation_history'][-4:]:
                messages.append({"role": msg['role'], "content": msg['content']})
        
        messages.append({"role": "user", "content": user_input})
        
        return self._call_api(messages, temperature=0.7)
    
    def _call_api(self, messages, temperature=0.1) -> str:
        """调用DeepSeek API"""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            return f"API调用失败: {e}"