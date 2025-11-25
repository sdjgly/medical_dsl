import os
import sys
import json
import time
from typing import List, Dict, Any

TEST_RESULTS_DIR = r"D:\medical_dsl\test_results"
os.makedirs(TEST_RESULTS_DIR, exist_ok=True)

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

from llm_client import ZhipuAIClient

class RealAPITester:
    """真实API测试类"""
    
    def __init__(self):
        self.test_results = {}
        self.api_key = os.getenv("ZHIPU_API_KEY")
        
        if not self.api_key:
            print("错误：未设置ZHIPU_API_KEY环境变量")
            print("请设置环境变量：")
            print("   Windows: set ZHIPU_API_KEY=your_api_key_here")
            print("   Linux/Mac: export ZHIPU_API_KEY=your_api_key_here")
            sys.exit(1)
        
        self.client = ZhipuAIClient(api_key=self.api_key)
    
    def test_intent_recognition_real(self):
        """测试真实意图识别"""
        print("\n测试真实意图识别")
        
        test_cases = [
            {
                "name": "医疗挂号意图",
                "user_input": "我想预约挂号看内科",
                "candidate_intents": ["挂号", "体检", "科普", "退出"],
                "expected_intent": "挂号"
            },
            {
                "name": "电商购买意图", 
                "user_input": "我要买一部手机",
                "candidate_intents": ["购买", "投诉", "退款", "客服"],
                "expected_intent": "购买"
            },
            {
                "name": "医疗体检意图",
                "user_input": "我想做个全面体检",
                "candidate_intents": ["挂号", "体检", "科普", "退出"],
                "expected_intent": "体检"
            },
            {
                "name": "电商投诉意图",
                "user_input": "我要投诉商品质量问题",
                "candidate_intents": ["购买", "投诉", "退款", "客服"],
                "expected_intent": "投诉"
            },
            {
                "name": "未知意图",
                "user_input": "今天天气怎么样",
                "candidate_intents": ["挂号", "体检", "科普", "退出"],
                "expected_intent": "unknown"
            }
        ]
        
        results = []
        total_passed = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   测试 {i}: {test_case['name']}")
            print(f"      用户输入: {test_case['user_input']}")
            print(f"      候选意图: {test_case['candidate_intents']}")
            print(f"      期望意图: {test_case['expected_intent']}")
            
            try:
                start_time = time.time()
                actual_intent = self.client.recognize_intent(
                    test_case["user_input"],
                    test_case["candidate_intents"]
                )
                response_time = time.time() - start_time
                
                passed = actual_intent == test_case["expected_intent"]
                if passed:
                    total_passed += 1
                
                result = {
                    "test_case": test_case["name"],
                    "user_input": test_case["user_input"],
                    "candidate_intents": test_case["candidate_intents"],
                    "expected_intent": test_case["expected_intent"],
                    "actual_intent": actual_intent,
                    "response_time": round(response_time, 2),
                    "passed": passed
                }
                results.append(result)
                
                status = "通过" if passed else "失败"
                print(f"      实际意图: {actual_intent}")
                print(f"      响应时间: {response_time:.2f}秒")
                print(f"      结果: {status}")
                
                # 添加延迟避免API限制
                time.sleep(1)
                
            except Exception as e:
                print(f"      测试失败: {e}")
                results.append({
                    "test_case": test_case["name"],
                    "error": str(e),
                    "passed": False
                })
        
        self.test_results["intent_recognition_real"] = {
            "scenario": "真实意图识别测试",
            "total_cases": len(test_cases),
            "passed_cases": total_passed,
            "pass_rate": f"{(total_passed/len(test_cases))*100:.1f}%",
            "detailed_results": results
        }
        
        return total_passed == len(test_cases)
    
    def test_generate_reply_real(self):
        """测试真实回复生成"""
        print("\n测试真实回复生成")
        
        test_cases = [
            {
                "name": "医疗健康咨询",
                "user_input": "我最近经常失眠，有什么建议吗？",
                "context": {
                    "script_module": "medical",
                    "conversation_history": [
                        {"role": "assistant", "content": "您好，这里是智慧医院综合服务中心，请问需要什么帮助？"},
                        {"role": "user", "content": "我睡眠不好"}
                    ]
                },
                "expected_keywords": ["睡眠", "建议", "医生", "休息", "习惯"]
            },
            {
                "name": "电商售后服务",
                "user_input": "我买的手机屏幕碎了，能保修吗？",
                "context": {
                    "script_module": "ecommerce", 
                    "conversation_history": [
                        {"role": "assistant", "content": "您好，欢迎来到智慧商城，请问需要什么帮助？"},
                        {"role": "user", "content": "我的手机有问题"}
                    ]
                },
                "expected_keywords": ["保修", "屏幕", "联系", "客服", "处理"]
            },
            {
                "name": "医疗症状咨询",
                "user_input": "我喉咙痛了三天，应该怎么办？",
                "context": {
                    "script_module": "medical",
                    "conversation_history": [
                        {"role": "assistant", "content": "您好，这里是智慧医院综合服务中心，请问需要什么帮助？"},
                        {"role": "user", "content": "我喉咙不舒服"}
                    ]
                },
                "expected_keywords": ["喉咙", "建议", "医生", "检查", "治疗"]
            },
            {
                "name": "电商订单问题",
                "user_input": "我的订单已经三天了还没发货",
                "context": {
                    "script_module": "ecommerce",
                    "conversation_history": [
                        {"role": "assistant", "content": "您好，欢迎来到智慧商城，请问需要什么帮助？"},
                        {"role": "user", "content": "我的订单有问题"}
                    ]
                },
                "expected_keywords": ["订单", "发货", "查询", "客服", "处理"]
            }
        ]
        
        results = []
        total_passed = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   测试 {i}: {test_case['name']}")
            print(f"      用户输入: {test_case['user_input']}")
            print(f"      场景模块: {test_case['context']['script_module']}")
            print(f"      期望关键词: {test_case['expected_keywords']}")
            
            try:
                start_time = time.time()
                actual_reply = self.client.generate_reply(
                    test_case["user_input"],
                    test_case["context"]
                )
                response_time = time.time() - start_time
                
                # 检查回复中是否包含期望的关键词
                contains_keywords = any(keyword in actual_reply for keyword in test_case["expected_keywords"])
                passed = contains_keywords and len(actual_reply) > 0
                if passed:
                    total_passed += 1
                
                result = {
                    "test_case": test_case["name"],
                    "user_input": test_case["user_input"],
                    "context_module": test_case["context"]["script_module"],
                    "expected_keywords": test_case["expected_keywords"],
                    "actual_reply": actual_reply,
                    "response_time": round(response_time, 2),
                    "contains_keywords": contains_keywords,
                    "reply_length": len(actual_reply),
                    "passed": passed
                }
                results.append(result)
                
                status = "通过" if passed else "失败"
                print(f"      生成回复: {actual_reply}")
                print(f"      回复长度: {len(actual_reply)} 字符")
                print(f"      包含关键词: {contains_keywords}")
                print(f"      响应时间: {response_time:.2f}秒")
                print(f"      结果: {status}")
                
                # 添加延迟避免API限制
                time.sleep(1)
                
            except Exception as e:
                print(f"      测试失败: {e}")
                results.append({
                    "test_case": test_case["name"],
                    "error": str(e),
                    "passed": False
                })
        
        self.test_results["generate_reply_real"] = {
            "scenario": "真实回复生成测试",
            "total_cases": len(test_cases),
            "passed_cases": total_passed,
            "pass_rate": f"{(total_passed/len(test_cases))*100:.1f}%",
            "detailed_results": results
        }
        
        return total_passed == len(test_cases)
    
    def test_api_performance(self):
        """测试API性能"""
        print("\n测试API性能")
        
        test_queries = [
            "你好",
            "我想咨询一下",
            "有什么可以帮我的吗",
            "测试性能",
            "简单回复"
        ]
        
        response_times = []
        successful_calls = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"   执行性能测试 {i}/5...")
            
            try:
                start_time = time.time()
                result = self.client.recognize_intent(query, ["测试"])
                response_time = time.time() - start_time
                response_times.append(response_time)
                successful_calls += 1
                
                print(f"      查询: '{query}' -> 响应时间: {response_time:.2f}秒")
                
                # 添加延迟避免API限制
                time.sleep(0.5)
                
            except Exception as e:
                print(f"      查询失败: {e}")
                response_times.append(None)
        
        if response_times:
            valid_times = [t for t in response_times if t is not None]
            if valid_times:
                avg_response_time = sum(valid_times) / len(valid_times)
                max_response_time = max(valid_times)
                min_response_time = min(valid_times)
                
                performance_passed = avg_response_time < 5.0  # 平均响应时间小于5秒为通过
                
                self.test_results["api_performance"] = {
                    "scenario": "API性能测试",
                    "total_queries": len(test_queries),
                    "successful_queries": successful_calls,
                    "success_rate": f"{(successful_calls/len(test_queries))*100:.1f}%",
                    "avg_response_time": round(avg_response_time, 2),
                    "max_response_time": round(max_response_time, 2),
                    "min_response_time": round(min_response_time, 2),
                    "passed": performance_passed
                }
                
                print(f"\n   性能统计:")
                print(f"      总查询数: {len(test_queries)}")
                print(f"      成功查询: {successful_calls}")
                print(f"      成功率: {(successful_calls/len(test_queries))*100:.1f}%")
                print(f"      平均响应时间: {avg_response_time:.2f}秒")
                print(f"      最大响应时间: {max_response_time:.2f}秒") 
                print(f"      最小响应时间: {min_response_time:.2f}秒")
                print(f"      结果: {'通过' if performance_passed else '失败'}")
                
                return performance_passed
        
        self.test_results["api_performance"] = {
            "scenario": "API性能测试",
            "error": "所有查询都失败",
            "passed": False
        }
        
        return False
    
    def run_all_tests(self):
        """运行所有真实API测试"""
        print("开始真实API测试")
        print(f"API密钥: {self.api_key[:10]}...{self.api_key[-5:]}" if len(self.api_key) > 15 else self.api_key)
        print("注意：真实API测试会产生实际费用")
        print("=" * 60)
        
        tests = [
            self.test_intent_recognition_real,
            self.test_generate_reply_real,
            self.test_api_performance
        ]
        
        test_names = [
            "真实意图识别测试",
            "真实回复生成测试", 
            "API性能测试"
        ]
        
        for test_func, test_name in zip(tests, test_names):
            try:
                print(f"\n{'='*50}")
                print(f"执行: {test_name}")
                print(f"{'='*50}")
                
                passed = test_func()
                status = "通过" if passed else "失败"
                print(f"\n{status}: {test_name}")
                
            except Exception as e:
                print(f"测试执行错误: {e}")
                self.test_results[test_func.__name__] = {
                    "scenario": test_name,
                    "error": str(e),
                    "passed": False
                }

        return self.test_results

def save_real_api_results(results, filename="llm_client_api_test_results.json"):
    """保存真实API测试结果到文件"""
    try:
        output_path = os.path.join(TEST_RESULTS_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"真实API测试结果已保存到: {output_path}")
    except Exception as e:
        print(f"保存真实API测试结果失败: {e}")

def main():
    """主函数"""
    tester = RealAPITester()
    
    # 运行测试
    test_results = tester.run_all_tests()
    
    # 保存结果
    save_real_api_results(test_results)
    
    # 检查总体结果
    passed_count = sum(1 for result in test_results.values() if result.get("passed", False))
    total_count = len(test_results)
    
    return passed_count == total_count

if __name__ == "__main__":    
    confirm = input("\n确认继续真实API测试？(y/N): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        success = main()
        sys.exit(0 if success else 1)
    else:
        print("用户取消真实API测试")
        sys.exit(0)