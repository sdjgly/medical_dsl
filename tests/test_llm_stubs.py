#!/usr/bin/env python3
"""
LLM客户端测试桩
用于模拟API响应和测试场景
"""

from typing import List, Dict, Any

class MockResponse:
    """模拟requests响应对象"""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP Error: {self.status_code}")

class MockRequests:
    """模拟requests模块"""
    
    def __init__(self):
        self.call_history = []
        self.responses = []
        
        # 添加exceptions属性以匹配requests模块
        class MockExceptions:
            class RequestException(Exception):
                pass
        
        self.exceptions = MockExceptions()
    
    def set_responses(self, responses):
        """设置预定义的响应序列"""
        self.responses = responses
    
    def post(self, url, headers=None, json=None, timeout=None):
        """模拟POST请求"""
        self.call_history.append({
            "method": "POST",
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout
        })
        
        if self.responses:
            response = self.responses.pop(0)
            # 如果响应是异常，则抛出
            if isinstance(response, Exception):
                raise response
            return response
        else:
            # 默认成功响应
            return MockResponse({
                "choices": [
                    {
                        "message": {
                            "content": "模拟AI回复内容"
                        }
                    }
                ]
            })

# 测试数据
TEST_SCENARIOS = {
    "medical_intent": {
        "user_input": "我想预约挂号",
        "candidate_intents": ["挂号", "体检", "科普", "退出"],
        "expected_intent": "挂号"
    },
    "ecommerce_intent": {
        "user_input": "我要买手机",
        "candidate_intents": ["购买", "投诉", "退款", "客服"],
        "expected_intent": "购买"
    },
    "unknown_intent": {
        "user_input": "今天天气怎么样",
        "candidate_intents": ["挂号", "体检", "科普", "退出"],
        "expected_intent": "unknown"
    },
    "medical_reply": {
        "user_input": "我最近头疼怎么办",
        "context": {
            "script_module": "medical",
            "conversation_history": [
                {"role": "assistant", "content": "您好，这里是智慧医院综合服务中心，请问需要什么帮助？"},
                {"role": "user", "content": "我最近头疼"}
            ]
        },
        "expected_keywords": ["建议", "医生", "休息", "医院"]  # 期望回复中包含的关键词
    },
    "ecommerce_reply": {
        "user_input": "手机质量有问题",
        "context": {
            "script_module": "ecommerce",
            "conversation_history": [
                {"role": "assistant", "content": "您好，欢迎来到智慧商城，请问需要什么帮助？"},
                {"role": "user", "content": "我要投诉"}
            ]
        },
        "expected_keywords": ["抱歉", "处理", "联系", "解决"]
    }
}