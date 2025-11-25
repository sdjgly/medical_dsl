import sys
import os
import json
from unittest.mock import patch


TEST_RESULTS_DIR = r"D:\medical_dsl\test_results"
os.makedirs(TEST_RESULTS_DIR, exist_ok=True)

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

from test_llm_stubs import MockResponse, MockRequests, TEST_SCENARIOS

# 导入要测试的模块
try:
    from llm_client import ZhipuAIClient
except ImportError as e:
    print(f"无法导入ZhipuAIClient: {e}")
    sys.exit(1)

class TestZhipuAIClient:
    """ZhipuAI客户端测试类"""
    
    def __init__(self):
        self.test_results = {}
    
    def test_intent_recognition_medical(self):
        """测试医疗场景意图识别"""
        print("\n测试医疗场景意图识别")
        
        scenario = TEST_SCENARIOS["medical_intent"]
        
        # 模拟API响应
        mock_response = MockResponse({
            "choices": [
                {
                    "message": {
                        "content": scenario["expected_intent"]
                    }
                }
            ]
        })
        mock_requests = MockRequests()
        mock_requests.set_responses([mock_response])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.recognize_intent(
                scenario["user_input"], 
                scenario["candidate_intents"]
            )
        
        passed = result == scenario["expected_intent"]
        self.test_results["intent_recognition_medical"] = {
            "scenario": "医疗意图识别",
            "user_input": scenario["user_input"],
            "candidate_intents": scenario["candidate_intents"],
            "expected_intent": scenario["expected_intent"],
            "actual_intent": result,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   用户输入: {scenario['user_input']}")
        print(f"   期望意图: {scenario['expected_intent']}")
        print(f"   实际意图: {result}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_intent_recognition_ecommerce(self):
        """测试电商场景意图识别"""
        print("\n测试电商场景意图识别")
        
        scenario = TEST_SCENARIOS["ecommerce_intent"]
        
        # 模拟API响应
        mock_response = MockResponse({
            "choices": [
                {
                    "message": {
                        "content": scenario["expected_intent"]
                    }
                }
            ]
        })
        mock_requests = MockRequests()
        mock_requests.set_responses([mock_response])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.recognize_intent(
                scenario["user_input"], 
                scenario["candidate_intents"]
            )
        
        passed = result == scenario["expected_intent"]
        self.test_results["intent_recognition_ecommerce"] = {
            "scenario": "电商意图识别",
            "user_input": scenario["user_input"],
            "candidate_intents": scenario["candidate_intents"],
            "expected_intent": scenario["expected_intent"],
            "actual_intent": result,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   用户输入: {scenario['user_input']}")
        print(f"   期望意图: {scenario['expected_intent']}")
        print(f"   实际意图: {result}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_intent_recognition_unknown(self):
        """测试未知意图识别"""
        print("\n测试未知意图识别")
        
        scenario = TEST_SCENARIOS["unknown_intent"]
        
        # 模拟API响应返回不在候选列表中的意图
        mock_response = MockResponse({
            "choices": [
                {
                    "message": {
                        "content": "天气"  # 不在候选列表中
                    }
                }
            ]
        })
        mock_requests = MockRequests()
        mock_requests.set_responses([mock_response])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.recognize_intent(
                scenario["user_input"], 
                scenario["candidate_intents"]
            )
        
        passed = result == scenario["expected_intent"]
        self.test_results["intent_recognition_unknown"] = {
            "scenario": "未知意图识别",
            "user_input": scenario["user_input"],
            "candidate_intents": scenario["candidate_intents"],
            "expected_intent": scenario["expected_intent"],
            "actual_intent": result,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   用户输入: {scenario['user_input']}")
        print(f"   期望意图: {scenario['expected_intent']}")
        print(f"   实际意图: {result}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_generate_reply_medical(self):
        """测试医疗场景回复生成"""
        print("\n测试医疗场景回复生成")
        
        scenario = TEST_SCENARIOS["medical_reply"]
        
        # 模拟API响应
        mock_response = MockResponse({
            "choices": [
                {
                    "message": {
                        "content": "建议您多休息，如果症状持续请及时就医咨询专业医生。"
                    }
                }
            ]
        })
        mock_requests = MockRequests()
        mock_requests.set_responses([mock_response])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.generate_reply(
                scenario["user_input"], 
                scenario["context"]
            )
        
        # 检查回复中是否包含期望的关键词
        contains_keywords = any(keyword in result for keyword in scenario["expected_keywords"])
        passed = contains_keywords and len(result) > 0
        
        self.test_results["generate_reply_medical"] = {
            "scenario": "医疗回复生成",
            "user_input": scenario["user_input"],
            "context": scenario["context"],
            "expected_keywords": scenario["expected_keywords"],
            "actual_reply": result,
            "contains_keywords": contains_keywords,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   用户输入: {scenario['user_input']}")
        print(f"   场景模块: {scenario['context']['script_module']}")
        print(f"   生成回复: {result}")
        print(f"   包含关键词: {contains_keywords}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_generate_reply_ecommerce(self):
        """测试电商场景回复生成"""
        print("\n测试电商场景回复生成")
        
        scenario = TEST_SCENARIOS["ecommerce_reply"]
        
        # 模拟API响应
        mock_response = MockResponse({
            "choices": [
                {
                    "message": {
                        "content": "非常抱歉给您带来不便，我们会尽快处理您的问题并联系您。"
                    }
                }
            ]
        })
        mock_requests = MockRequests()
        mock_requests.set_responses([mock_response])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.generate_reply(
                scenario["user_input"], 
                scenario["context"]
            )
        
        # 检查回复中是否包含期望的关键词
        contains_keywords = any(keyword in result for keyword in scenario["expected_keywords"])
        passed = contains_keywords and len(result) > 0
        
        self.test_results["generate_reply_ecommerce"] = {
            "scenario": "电商回复生成",
            "user_input": scenario["user_input"],
            "context": scenario["context"],
            "expected_keywords": scenario["expected_keywords"],
            "actual_reply": result,
            "contains_keywords": contains_keywords,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   用户输入: {scenario['user_input']}")
        print(f"   场景模块: {scenario['context']['script_module']}")
        print(f"   生成回复: {result}")
        print(f"   包含关键词: {contains_keywords}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_api_error_handling(self):
        """测试API错误处理"""
        print("\n测试API错误处理")
        
        # 模拟网络异常
        mock_requests = MockRequests()
        network_exception = mock_requests.exceptions.RequestException("模拟网络错误")
        mock_requests.set_responses([network_exception])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.recognize_intent("测试输入", ["选项1", "选项2"])
        
        passed = "错误" in result or "失败" in result or "不可用" in result or result == "unknown"
        self.test_results["api_error_handling"] = {
            "scenario": "API错误处理",
            "user_input": "测试输入",
            "candidate_intents": ["选项1", "选项2"],
            "actual_result": result,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   API错误响应: {result}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_http_error_handling(self):
        """测试HTTP错误处理"""
        print("\n测试HTTP错误处理")
        
        # 模拟HTTP 500错误
        mock_response = MockResponse({}, status_code=500)
        mock_requests = MockRequests()
        mock_requests.set_responses([mock_response])
        
        with patch('llm_client.requests', mock_requests):
            client = ZhipuAIClient(api_key="test_key")
            result = client.recognize_intent("测试输入", ["选项1", "选项2"])
        
        passed = "错误" in result or "失败" in result or "不可用" in result or result == "unknown"
        self.test_results["http_error_handling"] = {
            "scenario": "HTTP错误处理",
            "user_input": "测试输入",
            "candidate_intents": ["选项1", "选项2"],
            "actual_result": result,
            "passed": passed,
            "api_calls": mock_requests.call_history
        }
        
        print(f"   HTTP错误响应: {result}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed
    
    def test_no_api_key(self):
        """测试无API密钥情况"""
        print("\n测试无API密钥情况")
        
        client = ZhipuAIClient(api_key=None)
        result = client.recognize_intent("测试输入", ["选项1", "选项2"])
        
        passed = "AI功能未启用" in result
        self.test_results["no_api_key"] = {
            "scenario": "无API密钥",
            "user_input": "测试输入",
            "candidate_intents": ["选项1", "选项2"],
            "actual_result": result,
            "passed": passed,
            "api_calls": []
        }
        
        print(f"   无API密钥响应: {result}")
        print(f"   结果: {'通过' if passed else '失败'}")
        
        return passed

    def run_all_tests(self):
        """运行所有测试"""
        print("开始LLM客户端测试")
        print("测试ZhipuAI客户端的各种功能")
        
        # 获取所有测试方法
        test_methods = [method for method in dir(self) if method.startswith('test_') and callable(getattr(self, method))]
        
        for test_method in test_methods:
            try:
                passed = getattr(self, test_method)()
                status = "通过" if passed else "失败"
                print(f"   {status}: {test_method}")
            except Exception as e:
                print(f"   错误: {test_method} - {e}")
                self.test_results[test_method] = {
                    "scenario": test_method,
                    "error": str(e),
                    "passed": False
                }
        
        return self.test_results

def save_test_results(results, filename="llm_client_test_results.json"):
    """保存测试结果到文件"""
    # 清理结果，移除不可JSON序列化的对象
    cleaned_results = {}
    for test_name, result in results.items():
        cleaned_result = {}
        for key, value in result.items():
            if key == "api_calls":
                # 简化API调用记录
                cleaned_result[key] = [
                    {
                        "url": call.get("url", ""),
                        "method": call.get("method", ""),
                        "has_headers": "headers" in call,
                        "has_json": "json" in call
                    }
                    for call in value
                ]
            elif key == "context" and isinstance(value, dict):
                # 简化上下文
                cleaned_result[key] = {
                    "script_module": value.get("script_module", ""),
                    "conversation_history_length": len(value.get("conversation_history", []))
                }
            else:
                cleaned_result[key] = value
        cleaned_results[test_name] = cleaned_result
    
    try:
        output_path = os.path.join(TEST_RESULTS_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_results, f, ensure_ascii=False, indent=2)
        print(f"   测试结果已保存到: {output_path}")
    except Exception as e:
        print(f"   保存测试结果失败: {e}")

def main():
    """主函数"""
    tester = TestZhipuAIClient()
    
    # 运行测试
    test_results = tester.run_all_tests()
    
    # 统计结果
    passed_count = sum(1 for result in test_results.values() if result.get("passed", False))
    total_count = len(test_results)
    
    print(f"\n测试总结:")
    print(f"   总测试数: {total_count}")
    print(f"   通过数: {passed_count}")
    print(f"   失败数: {total_count - passed_count}")
    
    if passed_count == total_count:
        print("所有测试都通过!")
    else:
        print("部分测试失败，请检查详细信息")
    
    # 保存结果
    save_test_results(test_results)
    
    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)