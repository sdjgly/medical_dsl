import requests
import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ZhipuAIClient:    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        
    def recognize_intent(self, user_input: str, candidate_intents: List[str]) -> str:
        """意图识别"""

        # 检查API密钥
        if not self.api_key:
            return "AI功能未启用：请设置API_KEY环境变量"
        
        prompt = f"""
            请严格分析用户输入的意图，并从以下候选意图中选择最匹配的一个：

            候选意图列表：{', '.join(candidate_intents)}

            用户输入："{user_input}"

            分析要求：
            1. 仔细理解用户输入的真实意图
            2. 选择最匹配的候选意图
            3. 如果用户输入明显匹配某个意图，就返回该意图名称
            4. 如果完全不匹配任何意图，返回 "unknown"

            请只返回意图名称，不要任何其他解释、标点或空格。

            示例：
            用户输入："我想看病挂号" -> 挂号
            用户输入："我要体检" -> 体检
            用户输入："今天天气" -> unknown
            """
        
        response = self._call_api(prompt, temperature=0.1)
        
        # 如果返回的是错误消息，直接返回unknown
        if "错误" in response or "失败" in response or "不可用" in response or "未启用" in response:
            return "unknown"

        # 清理响应，确保只返回意图名称
        intent = response.strip().strip('"\'')
        
        # 验证意图是否在候选列表中
        if intent in candidate_intents:
            return intent
        else:
            return "unknown"
    
    def generate_reply(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """生成智能回复"""
        script_module = context.get('script_module', '通用') if context else '通用'
        
        # 根据模块类型提供不同的系统提示
        system_prompts = {
            "medical": """
                你是智慧医院的专业客服助手，请提供专业、友好的医疗健康咨询服务。

                回复要求：
                1. 专业准确：提供准确的医疗信息和健康建议
                2. 友好亲切：语气温和，体现人文关怀
                3. 安全边界：只能提供健康建议和医疗科普，不能进行诊断或开处方
                4. 及时转诊：涉及具体病症时建议咨询专业医生

                注意：严格遵守医疗安全规范，不提供超出健康咨询范围的服务。
            """,
            "ecommerce": """
                你是智慧商城的专业客服助手，请提供热情、专业的电商咨询服务。

                回复要求：
                1. 专业热情：准确介绍商品信息，热情服务客户
                2. 解决问题：帮助处理订单、投诉、退款等问题
                3. 促进转化：适当推荐相关商品，提升购物体验
                4. 售后支持：妥善处理客户反馈和问题

                注意：诚实守信，不夸大宣传，切实维护消费者权益。
            """,
            "default": """
                你是专业的智能客服助手，请根据对话上下文提供准确、友好的服务。

                通用要求：
                1. 准确理解：准确把握用户需求和问题
                2. 专业回复：基于知识提供准确信息
                3. 友好耐心：保持友好态度，耐心解答
                4. 解决问题：切实帮助用户解决实际问题
            """
        }
        
        system_prompt = system_prompts.get(script_module.lower(), system_prompts["default"])
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史
        if context and 'conversation_history' in context:
            for msg in context['conversation_history'][-6:]:  # 最近3轮对话
                messages.append({"role": msg['role'], "content": msg['content']})
        
        messages.append({"role": "user", "content": user_input})
        
        return self._call_api(messages, temperature=0.7)
    
    def _call_api(self, messages, temperature=0.1) -> str:
        """调用智谱AI API"""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        if not self.api_key:
            return "AI功能未启用：请设置ZHIPU_API_KEY环境变量"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 智谱AI的请求格式
        payload = {
            "model": "glm-4",  # 使用GLM-4模型
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
            # 智谱AI的响应格式
            return result["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            return f"网络错误：{e}"
        except KeyError:
            return "API响应格式错误"
        except Exception as e:
            return f"AI服务暂时不可用：{e}"