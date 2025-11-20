import sys
import os
import json
import io
import contextlib
import subprocess

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))  # tests目录
project_root = os.path.dirname(current_dir)  # medical_dsl目录
src_dir = os.path.join(project_root, "src")
database_dir = os.path.join(project_root, "database")

# 添加src目录到Python路径，以便导入interpreter
sys.path.insert(0, src_dir)

from test_stubs import MockDSLParser, MockLLMClient

# 导入interpreter
try:
    from interpreter import DSLInterpreter
except ImportError as e:
    print(f"无法导入DSLInterpreter: {e}")
    sys.exit(1)

def init_database():
    """初始化数据库"""
    try:
        init_db_path = os.path.join(database_dir, "init_db.py")
        if os.path.exists(init_db_path):
            print(f"运行数据库初始化脚本: {init_db_path}")
            result = subprocess.run([sys.executable, init_db_path], 
                                  capture_output=True, text=True, cwd=database_dir)
            if result.returncode == 0:
                print("数据库初始化成功")
                return True
            else:
                print(f"数据库初始化失败: {result.stderr}")
                return False
        else:
            print(f"找不到init_db.py文件: {init_db_path}")
            return False
    except Exception as e:
        print(f"数据库初始化异常: {e}")
        return False

class TestInterpreter:
    """测试解释器类"""
    
    def __init__(self):
        self.parser = MockDSLParser()
        self.llm_client = MockLLMClient()
        self.test_results = {}
    
    def capture_output(self, func, *args, **kwargs):
        """捕获函数的标准输出"""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            func(*args, **kwargs)
        return output.getvalue()
    
    def simulate_user_inputs(self, inputs):
        """模拟用户输入序列"""
        input_iterator = iter(inputs)
        return lambda prompt: next(input_iterator)
    
    def test_basic_flow(self):
        """测试基本流程"""
        print("\n测试基本流程")
        
        script_ast = self.parser.create_medical_script()
        interpreter = DSLInterpreter(script_ast, self.llm_client)
        
        # 模拟用户输入序列
        user_inputs = ["挂号", "内科", "退出"]
        interpreter.input_function = self.simulate_user_inputs(user_inputs)
        
        # 捕获输出
        try:
            output = self.capture_output(interpreter.run)
        except StopIteration:
            output = "测试完成"
        
        # 分析结果
        result = {
            "test_name": "基本流程测试",
            "user_inputs": user_inputs,
            "output_lines": output.split('\n') if isinstance(output, str) else [],
            "conversation_history": interpreter.conversation_history,
            "final_step": interpreter.current_step,
            "is_running": interpreter.is_running,
            "llm_calls": self.llm_client.call_history
        }
        
        # 验证结果
        result["passed"] = (
            not interpreter.is_running and 
            len(interpreter.conversation_history) >= 3
        )
        
        return result
    
    def test_ai_reply_flow(self):
        """测试AI回复流程"""
        print("\n测试AI回复流程")
        
        script_ast = self.parser.create_medical_script()
        interpreter = DSLInterpreter(script_ast, self.llm_client)
        
        # 模拟用户输入序列
        user_inputs = ["挂号", "ai", "测试问题", "退出"]
        interpreter.input_function = self.simulate_user_inputs(user_inputs)
        
        # 捕获输出
        try:
            output = self.capture_output(interpreter.run)
        except StopIteration:
            output = "测试完成"
        
        # 分析结果
        result = {
            "test_name": "AI回复流程测试",
            "user_inputs": user_inputs,
            "output_lines": output.split('\n') if isinstance(output, str) else [],
            "conversation_history": interpreter.conversation_history,
            "final_step": interpreter.current_step,
            "is_running": interpreter.is_running,
            "llm_calls": self.llm_client.call_history
        }
        
        # 验证结果
        ai_reply_calls = [call for call in self.llm_client.call_history if call["method"] == "generate_reply"]
        result["passed"] = (
            len(ai_reply_calls) > 0 and
            len(interpreter.conversation_history) >= 3
        )
        
        return result
    
    def test_ecommerce_flow(self):
        """测试电商流程"""
        print("\n测试电商流程")
        
        # 初始化数据库
        if not init_database():
            print("数据库初始化失败，跳过电商流程测试")
            return {
                "test_name": "电商流程测试",
                "passed": False,
                "error": "数据库初始化失败"
            }
        
        script_ast = self.parser.create_ecommerce_script()
        # 使用真实数据库
        db_path = os.path.join(database_dir, "ecommerce.db")
        interpreter = DSLInterpreter(script_ast, self.llm_client, db_path)
        
        # 模拟用户输入序列
        user_inputs = ["购买", "手机", "2", "退出"]
        interpreter.input_function = self.simulate_user_inputs(user_inputs)
        
        # 捕获输出
        try:
            output = self.capture_output(interpreter.run)
        except StopIteration:
            output = "测试完成"
        
        # 分析结果
        result = {
            "test_name": "电商流程测试",
            "user_inputs": user_inputs,
            "output_lines": output.split('\n') if isinstance(output, str) else [],
            "conversation_history": interpreter.conversation_history,
            "final_step": interpreter.current_step,
            "is_running": interpreter.is_running,
            "llm_calls": self.llm_client.call_history,
            "variables": interpreter.variables
        }
        
        # 验证结果 - 现在应该显示有库存
        result["passed"] = (
            "手机有库存" in output and
            "下单成功" in output and
            "quantity" in interpreter.variables and
            interpreter.variables["quantity"] == "2"
        )
        
        if not result["passed"]:
            print(f"电商流程测试失败详情:")
            print(f"   输出包含'手机有库存': {'手机有库存' in output}")
            print(f"   输出包含'下单成功': {'下单成功' in output}")
            print(f"   变量quantity存在: {'quantity' in interpreter.variables}")
            if 'quantity' in interpreter.variables:
                print(f"   quantity值: {interpreter.variables['quantity']}")
            if 'stock' in interpreter.variables:
                print(f"   stock值: {interpreter.variables['stock']}")
        
        return result
    
    def test_fallback_flow(self):
        """测试回退流程"""
        print("\n测试回退流程")
        
        script_ast = self.parser.create_medical_script()
        interpreter = DSLInterpreter(script_ast, self.llm_client)
        
        # 模拟用户输入序列 - 使用未知意图
        user_inputs = ["未知指令", "挂号", "退出"]
        interpreter.input_function = self.simulate_user_inputs(user_inputs)
        
        # 捕获输出
        try:
            output = self.capture_output(interpreter.run)
        except StopIteration:
            output = "测试完成"
        
        # 分析结果
        result = {
            "test_name": "回退流程测试",
            "user_inputs": user_inputs,
            "output_lines": output.split('\n') if isinstance(output, str) else [],
            "conversation_history": interpreter.conversation_history,
            "final_step": interpreter.current_step,
            "is_running": interpreter.is_running,
            "llm_calls": self.llm_client.call_history
        }
        
        # 验证结果
        result["passed"] = (
            len(interpreter.conversation_history) >= 3 and
            not interpreter.is_running
        )
        
        return result
    
    def test_complaint_flow(self):
        """测试投诉流程"""
        print("\n测试投诉流程")
        
        script_ast = self.parser.create_ecommerce_script()
        interpreter = DSLInterpreter(script_ast, self.llm_client)
        
        # 模拟用户输入序列
        user_inputs = ["投诉", "商品质量有问题", "退出"]
        interpreter.input_function = self.simulate_user_inputs(user_inputs)
        
        # 捕获输出
        try:
            output = self.capture_output(interpreter.run)
        except StopIteration:
            output = "测试完成"
        
        # 分析结果
        result = {
            "test_name": "投诉流程测试",
            "user_inputs": user_inputs,
            "output_lines": output.split('\n') if isinstance(output, str) else [],
            "conversation_history": interpreter.conversation_history,
            "final_step": interpreter.current_step,
            "is_running": interpreter.is_running,
            "llm_calls": self.llm_client.call_history,
            "variables": interpreter.variables
        }
        
        # 验证结果
        result["passed"] = (
            "complaintText" in interpreter.variables and
            "商品质量有问题" in interpreter.variables["complaintText"] and
            len(self.llm_client.call_history) > 0
        )
        
        return result
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始DSL解释器测试")
        print("测试各种业务场景的对话流程")
        
        tests = [
            self.test_basic_flow,
            self.test_ai_reply_flow,
            self.test_ecommerce_flow,
            self.test_fallback_flow,
            self.test_complaint_flow
        ]
        
        for test_func in tests:
            test_name = test_func.__name__
            try:
                self.test_results[test_name] = test_func()
                status = "通过" if self.test_results[test_name]["passed"] else "失败"
                print(f"   {status}: {test_name}")
            except Exception as e:
                self.test_results[test_name] = {
                    "test_name": test_name,
                    "error": str(e),
                    "passed": False
                }
                print(f"   错误: {test_name} - {e}")
        
        # 统计结果
        passed_count = sum(1 for result in self.test_results.values() if result.get("passed", False))
        total_count = len(self.test_results)
        
        print(f"\n测试总结:")
        print(f"   总测试数: {total_count}")
        print(f"   通过数: {passed_count}")
        print(f"   失败数: {total_count - passed_count}")
        
        if passed_count == total_count:
            print("所有测试都通过!")
        else:
            print("部分测试失败，请检查详细信息")
        
        return passed_count == total_count
    
    def save_results(self, filename="interpreter_test_results.json"):
        """保存测试结果到文件"""
        # 清理输出，只保留关键信息
        cleaned_results = {}
        for test_name, result in self.test_results.items():
            cleaned_result = {
                "test_name": result.get("test_name", test_name),
                "passed": result.get("passed", False),
                "user_inputs": result.get("user_inputs", []),
                "final_step": result.get("final_step", "unknown"),
                "is_running": result.get("is_running", True),
                "variables": result.get("variables", {}),
                "llm_call_count": len(result.get("llm_calls", [])),
                "conversation_turns": len(result.get("conversation_history", [])),
                "error": result.get("error", None)
            }
            
            # 添加对话摘要
            if "conversation_history" in result:
                cleaned_result["conversation_summary"] = [
                    f"{msg['role']}: {msg['content'][:50]}..." if len(msg['content']) > 50 else f"{msg['role']}: {msg['content']}"
                    for msg in result["conversation_history"]
                ]
            
            cleaned_results[test_name] = cleaned_result
        
        try:
            output_path = os.path.join(current_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_results, f, ensure_ascii=False, indent=2)
            print(f"测试结果已保存到: {output_path}")
        except Exception as e:
            print(f"保存测试结果失败: {e}")

def main():
    """主函数"""
    tester = TestInterpreter()
    success = tester.run_all_tests()
    tester.save_results()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)