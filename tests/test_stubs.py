"""
测试桩文件
用于替代dsl_parser.py和llm_client.py进行interpreter测试
"""
from typing import Dict, List, Any

#DSL Parser 桩
class MockDSLParser:
    """模拟DSL解析器"""
    
    @staticmethod
    def create_medical_script():
        """创建医疗场景的测试脚本AST"""
        return {
            "module": "medical",
            "steps": {
                "welcome": {
                    "actions": [
                        {"type": "Speak", "message": "您好，这里是智慧医院综合服务中心，请问需要什么帮助？"},
                        {"type": "Listen"},
                        {"type": "Case", "pattern": "挂号", "target": "regDept"},
                        {"type": "Case", "pattern": "体检", "target": "checkupType"},
                        {"type": "Case", "pattern": "退出", "target": "goodbye"},
                        {"type": "Default", "target": "fallback"}
                    ]
                },
                "regDept": {
                    "actions": [
                        {"type": "Speak", "message": "好的，请问您想挂哪个科室？内科、外科、儿科还是妇科？"},
                        {"type": "Listen"},
                        {"type": "Case", "pattern": "内科", "target": "regConfirm"},
                        {"type": "Case", "pattern": "外科", "target": "regConfirm"},
                        {"type": "Case", "pattern": "ai", "target": "regAI"},
                        {"type": "Default", "target": "regDeptFallback"}
                    ]
                },
                "regDeptFallback": {
                    "actions": [
                        {"type": "Speak", "message": "抱歉，我没听清。可以告诉我要挂的科室吗？比如内科或外科。"},
                        {"type": "Goto", "target": "regDept"}
                    ]
                },
                "regAI": {
                    "actions": [
                        {"type": "AIReply"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "regConfirm": {
                    "actions": [
                        {"type": "Speak", "message": "预约成功！已为您挂号。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "checkupType": {
                    "actions": [
                        {"type": "Speak", "message": "我们提供基础体检、入职体检、老年体检。您想了解哪一种？"},
                        {"type": "Listen"},
                        {"type": "Case", "pattern": "基础", "target": "chkBasic"},
                        {"type": "Case", "pattern": "入职", "target": "chkJob"},
                        {"type": "Default", "target": "checkupFallback"}
                    ]
                },
                "checkupFallback": {
                    "actions": [
                        {"type": "Speak", "message": "抱歉，我没有听清。您可以说基础体检、入职体检或老年体检。"},
                        {"type": "Goto", "target": "checkupType"}
                    ]
                },
                "chkBasic": {
                    "actions": [
                        {"type": "Speak", "message": "基础体检包括血常规、B超、肝功能等项目，价格为299元。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "chkJob": {
                    "actions": [
                        {"type": "Speak", "message": "入职体检包含胸片、心电图和血检等项目，价格为399元。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "fallback": {
                    "actions": [
                        {"type": "Speak", "message": "我不太明白您的意思。您可以说挂号、体检、科普。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "goodbye": {
                    "actions": [
                        {"type": "Speak", "message": "感谢使用智慧医院助手，祝您健康平安！"},
                        {"type": "Exit"}
                    ]
                }
            }
        }
    
    @staticmethod
    def create_ecommerce_script():
        """创建电商场景的测试脚本AST - 修复版本"""
        return {
            "module": "ecommerce",
            "steps": {
                "welcome": {
                    "actions": [
                        {"type": "Speak", "message": "您好，欢迎来到智慧商城，请问需要什么帮助？"},
                        {"type": "Listen"},
                        {"type": "Case", "pattern": "购买", "target": "buyStart"},
                        {"type": "Case", "pattern": "投诉", "target": "complaintStart"},
                        {"type": "Case", "pattern": "退出", "target": "goodbye"},
                        {"type": "Default", "target": "fallback"}
                    ]
                },
                "buyStart": {
                    "actions": [
                        {"type": "Speak", "message": "好的，请告诉我想买什么商品？例如：手机、耳机、电脑。"},
                        {"type": "Listen"},
                        {"type": "Case", "pattern": "手机", "target": "buyPhone"},
                        {"type": "Case", "pattern": "耳机", "target": "buyEarphone"},
                        {"type": "Default", "target": "buyFallback"}
                    ]
                },
                "buyFallback": {
                    "actions": [
                        {"type": "Speak", "message": "暂时没听清，您可以说例如：手机、耳机、电脑。"},
                        {"type": "Goto", "target": "buyStart"}
                    ]
                },
                "buyPhone": {
                    "actions": [
                        {"type": "Speak", "message": "手机库存查询中，请稍候……"},
                        {"type": "Lock", "resource": "phone_stock"},
                        {"type": "DBQuery", "query": "SELECT stock FROM goods WHERE name='phone'", "variable": "stock", "target": "checkStock"}
                    ]
                },
                "checkStock": {
                    "actions": [
                        {"type": "If", "condition": {"left": "stock", "operator": "<=", "right": 0}, "target": "outOfStockPhone"},
                        {"type": "Speak", "message": "手机有库存。请问要买几台？"},
                        {"type": "ListenAssign", "variable": "quantity"},
                        {"type": "DBExec", "query": "UPDATE goods SET stock = stock - {quantity} WHERE name='phone'"},
                        {"type": "Unlock", "resource": "phone_stock"},
                        {"type": "Speak", "message": "下单成功！您购买了{quantity}台手机。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "outOfStockPhone": {
                    "actions": [
                        {"type": "Unlock", "resource": "phone_stock"},
                        {"type": "Speak", "message": "抱歉，手机目前缺货。要看看其他商品吗？"},
                        {"type": "Goto", "target": "buyStart"}
                    ]
                },
                "buyEarphone": {
                    "actions": [
                        {"type": "Speak", "message": "耳机库存查询中，请稍候……"},
                        {"type": "Lock", "resource": "earphone_stock"},
                        {"type": "DBQuery", "query": "SELECT stock FROM goods WHERE name='earphone'", "variable": "stock", "target": "checkEarphoneStock"}
                    ]
                },
                "checkEarphoneStock": {
                    "actions": [
                        {"type": "If", "condition": {"left": "stock", "operator": "<=", "right": 0}, "target": "outOfStockEarphone"},
                        {"type": "Speak", "message": "耳机有库存。请问要买几副？"},
                        {"type": "ListenAssign", "variable": "quantity"},
                        {"type": "DBExec", "query": "UPDATE goods SET stock = stock - {quantity} WHERE name='earphone'"},
                        {"type": "Unlock", "resource": "earphone_stock"},
                        {"type": "Speak", "message": "下单成功！您购买了{quantity}副耳机。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "outOfStockEarphone": {
                    "actions": [
                        {"type": "Unlock", "resource": "earphone_stock"},
                        {"type": "Speak", "message": "抱歉，耳机目前缺货。要看看其他商品吗？"},
                        {"type": "Goto", "target": "buyStart"}
                    ]
                },
                "complaintStart": {
                    "actions": [
                        {"type": "Speak", "message": "非常抱歉给您带来困扰，请告诉我您的投诉内容。"},
                        {"type": "ListenAssign", "variable": "complaintText"},
                        {"type": "AIReply"},
                        {"type": "Speak", "message": "您的投诉我们已经记录，会在24小时内联系您。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "fallback": {
                    "actions": [
                        {"type": "Speak", "message": "我不太明白您的意思。您可以说购买、投诉、退款或者联系客服。"},
                        {"type": "Goto", "target": "welcome"}
                    ]
                },
                "goodbye": {
                    "actions": [
                        {"type": "Speak", "message": "感谢使用智慧商城助手，祝您购物愉快！"},
                        {"type": "Exit"}
                    ]
                }
            }
        }

#LLM Client 桩
class MockLLMClient:
    """模拟LLM客户端"""
    
    def __init__(self):
        self.call_history = []
    
    def recognize_intent(self, user_input: str, candidate_intents: List[str]) -> str:
        """模拟意图识别"""
        self.call_history.append({
            "method": "recognize_intent",
            "user_input": user_input,
            "candidate_intents": candidate_intents
        })
        
        # 简单的意图匹配逻辑
        user_input_lower = user_input.lower()
        
        for intent in candidate_intents:
            if intent in user_input_lower:
                return intent
        
        return "unknown"
    
    def generate_reply(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """模拟生成回复"""
        self.call_history.append({
            "method": "generate_reply",
            "user_input": user_input,
            "context": context
        })
        
        script_module = context.get('script_module', '通用') if context else '通用'
        return f"[{script_module}场景] 这是对 '{user_input}' 的模拟AI回复"