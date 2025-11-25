import os
import sys
import time
from io import StringIO
from contextlib import redirect_stdout

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

from main import DSLChatbot

class TestRunner:    
    def __init__(self):
        self.results = {}
    
    def run_medical_tests(self):
        print("开始医疗模块测试...")
        
        test1_inputs = ["挂号", "内科", "今天", "退出"]
        test1_result = self.run_chatbot_test("medical", test1_inputs, "医疗-挂号流程")
        
        test2_inputs = ["体检", "基础", "退出"]
        test2_result = self.run_chatbot_test("medical", test2_inputs, "医疗-体检流程")
        
        test3_inputs = ["科普", "饮食", "退出"]
        test3_result = self.run_chatbot_test("medical", test3_inputs, "医疗-科普-饮食")
        
        test4_inputs = ["科普", "自由提问", "我最近失眠怎么办？", "退出"]
        test4_result = self.run_chatbot_test("medical", test4_inputs, "医疗-科普-自由提问")
        
        test5_inputs = ["未知指令", "挂号", "未知科室", "内科", "未知日期", "今天", "退出"]
        test5_result = self.run_chatbot_test("medical", test5_inputs, "医疗-错误输入处理")
        
        self.results["medical"] = {
            "test1": test1_result,
            "test2": test2_result,
            "test3": test3_result,
            "test4": test4_result,
            "test5": test5_result
        }
    
    def run_ecommerce_tests(self):
        print("开始电商模块测试...")
        
        from database.init_db import init_db
        init_db()
        
        test1_inputs = ["购买", "手机", "2", "退出"]
        test1_result = self.run_chatbot_test("ecommerce", test1_inputs, "电商-购买手机")
        
        test2_inputs = ["购买", "耳机", "1", "退出"]
        test2_result = self.run_chatbot_test("ecommerce", test2_inputs, "电商-购买耳机")
        
        test3_inputs = ["退款", "1001", "退出"]
        test3_result = self.run_chatbot_test("ecommerce", test3_inputs, "电商-退款成功")
        
        test4_inputs = ["退款", "1002", "退出"]
        test4_result = self.run_chatbot_test("ecommerce", test4_inputs, "电商-退款失败")
        
        test5_inputs = ["投诉", "商品质量有问题，屏幕有划痕", "退出"]
        test5_result = self.run_chatbot_test("ecommerce", test5_inputs, "电商-投诉流程")
        
        test6_inputs = ["购买", "手机", "8", "购买", "手机", "3", "退出"]
        test6_result = self.run_chatbot_test("ecommerce", test6_inputs, "电商-库存不足")
        
        self.results["ecommerce"] = {
            "test1": test1_result,
            "test2": test2_result,
            "test3": test3_result,
            "test4": test4_result,
            "test5": test5_result,
            "test6": test6_result
        }
    
    def run_chatbot_test(self, module, inputs, test_name):
        print(f"  运行测试: {test_name}")
        
        # 获取脚本路径
        scripts_dir = os.path.join(project_root, "scripts")
        script_path = os.path.join(scripts_dir, f"{module}.txt")
        
        # 设置数据库路径（仅电商需要）
        db_path = None
        if module == "ecommerce":
            db_path = os.path.join(project_root, "database", "ecommerce.db")
        
        # 创建聊天机器人实例
        chatbot = DSLChatbot(
            script_path=script_path,
            use_ai=True,
            db_path=db_path
        )
        
        # 模拟用户输入
        input_iterator = iter(inputs)
        original_input = chatbot.interpreter.input_function if hasattr(chatbot, 'interpreter') and chatbot.interpreter else None
        
        try:
            # 初始化聊天机器人
            if not chatbot.initialize():
                return {"error": "初始化失败", "inputs": inputs}
            
            # 替换输入函数
            chatbot.interpreter.input_function = lambda prompt: next(input_iterator)
            
            # 捕获输出
            output = StringIO()
            with redirect_stdout(output):
                chatbot.interpreter.run()
            
            return {
                "inputs": inputs,
                "output": output.getvalue(),
                "success": True
            }
            
        except StopIteration:
            # 正常结束，所有输入已消耗
            return {
                "inputs": inputs,
                "output": "测试正常完成",
                "success": True
            }
        except Exception as e:
            return {
                "inputs": inputs,
                "error": str(e),
                "success": False
            }
        finally:
            if original_input and chatbot.interpreter:
                chatbot.interpreter.input_function = original_input
    
    def save_results(self):
        """保存测试结果到文件"""
        import json
        from datetime import datetime
        
        # 创建结果目录
        results_dir = os.path.join(project_root, "test_results")
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_test_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # 清理输出，只保留关键信息
        cleaned_results = {}
        for module, tests in self.results.items():
            cleaned_results[module] = {}
            for test_name, result in tests.items():
                cleaned_result = {
                    "inputs": result.get("inputs", []),
                    "success": result.get("success", False),
                    "error": result.get("error", None)
                }
                
                if "output" in result:
                    lines = result["output"].split('\n')
                    key_lines = []
                    for line in lines:
                        if any(keyword in line for keyword in ["机器人:", "用户:", "步骤:", "已启动", "感谢使用"]):
                            key_lines.append(line)
                    cleaned_result["key_output"] = key_lines
                
                cleaned_results[module][test_name] = cleaned_result
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cleaned_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试结果已保存到: {filepath}")
        return filepath
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("开始DSL智能客服系统全面测试")
        print("=" * 60)
        
        # 运行医疗模块测试
        self.run_medical_tests()
        
        # 运行电商模块测试
        self.run_ecommerce_tests()
        
        # 保存结果
        result_file = self.save_results()
        
        # 统计结果
        total_tests = 0
        passed_tests = 0
        
        for module, tests in self.results.items():
            module_total = len(tests)
            module_passed = sum(1 for test in tests.values() if test.get("success", False))
            
            total_tests += module_total
            passed_tests += module_passed
            
            print(f"\n{module}模块: {module_passed}/{module_total} 测试通过")
        
        print(f"\n总体结果: {passed_tests}/{total_tests} 测试通过")
        
        return passed_tests == total_tests

def main():
    tester = TestRunner()
    success = tester.run_all_tests()
    
    # 返回退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()