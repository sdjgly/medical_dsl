import sys
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from dsl_parser import parse_script  # 或者您选择的新名称

def run_test(test_name, test_script, expected_keys=None):
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"{'='*60}")
    
    try:
        result = parse_script(test_script)
        print("解析成功!")
        
        # 打印AST结构
        print("\n解析结果:")
        print(f"  模块: {result.get('module', '未设置')}")
        print(f"  步骤数量: {len(result.get('steps', {}))}")
        
        # 打印每个步骤的详细信息
        for step_name, step_data in result.get('steps', {}).items():
            print(f"\n   步骤 '{step_name}':")
            for i, action in enumerate(step_data.get('actions', []), 1):
                action_type = action.get('type', '未知')
                if action_type == 'Speak':
                    print(f"    {i}. Speak: \"{action.get('message', '')}\"")
                elif action_type == 'Listen':
                    print(f"    {i}. Listen")
                elif action_type == 'ListenAssign':
                    print(f"    {i}. Listen assign {action.get('variable', '')}")
                elif action_type == 'Case':
                    print(f"    {i}. Case \"{action.get('pattern', '')}\" -> goto {action.get('target', '')}")
                elif action_type == 'Default':
                    print(f"    {i}. Default -> goto {action.get('target', '')}")
                elif action_type == 'Goto':
                    print(f"    {i}. goto {action.get('target', '')}")
                elif action_type == 'AIReply':
                    print(f"    {i}. AIReply")
                elif action_type == 'Exit':
                    print(f"    {i}. Exit")
                elif action_type == 'Lock':
                    print(f"    {i}. Lock \"{action.get('resource', '')}\"")
                elif action_type == 'Unlock':
                    print(f"    {i}. Unlock \"{action.get('resource', '')}\"")
                elif action_type == 'DBQuery':
                    print(f"    {i}. DBQuery \"{action.get('query', '')}\" -> goto {action.get('target', '')} {action.get('variable', '')}")
                elif action_type == 'DBExec':
                    print(f"    {i}. DBExec \"{action.get('query', '')}\"")
                elif action_type == 'If':
                    condition = action.get('condition', {})
                    print(f"    {i}. If {condition.get('left', '')} {condition.get('operator', '')} {condition.get('right', '')} -> goto {action.get('target', '')}")
                else:
                    print(f"    {i}. {action_type}: {action}")
        
        # 验证预期键
        if expected_keys:
            missing_keys = [key for key in expected_keys if key not in result]
            if missing_keys:
                print(f"缺少预期键: {missing_keys}")
            else:
                print("所有预期键都存在")
        
        # 返回结果用于进一步验证
        return result
        
    except Exception as e:
        print(f"解析失败: {e}")
        return None

def test_basic_syntax():
    """测试基础语法"""
    test_script = '''
module "基础测试"

Step welcome
    Speak "欢迎使用测试系统"
    Listen
    Case "选项1" -> goto step1
    Case "选项2" -> goto step2
    Default -> goto fallback

Step step1
    Speak "您选择了选项1"
    goto welcome

Step step2
    Speak "您选择了选项2" 
    goto welcome

Step fallback
    Speak "没有听懂您的选择"
    goto welcome
'''
    return run_test("基础语法测试", test_script, ['module', 'steps'])

def test_advanced_features():
    """测试高级功能"""
    test_script = '''
module "高级功能测试"

Step complex
    Speak "测试高级功能"
    Listen assign user_input
    If user_input == "10" -> goto process_number
    If user_input == "yes" -> goto confirm
    DBQuery "SELECT count FROM table" -> goto check_result count_var
    Lock "resource_1"
    DBExec "UPDATE table SET count = count + 1"
    Unlock "resource_1"
    AIReply
    Exit

Step process_number
    Speak "处理数字输入"
    goto complex

Step confirm
    Speak "确认操作"
    goto complex

Step check_result
    Speak "检查结果"
    goto complex
'''
    return run_test("高级功能测试", test_script, ['module', 'steps'])

def test_medical_script():
    """测试医疗脚本片段"""
    test_script = '''
module "medical"

Step welcome
    Speak "您好，这里是智慧医院综合服务中心，请问需要什么帮助？"
    Listen
    Case "挂号" -> goto regDept
    Case "预约" -> goto regDept
    Case "体检" -> goto checkupType
    Case "科普" -> goto scienceIntro
    Case "退出" -> goto goodbye
    Default -> goto fallback

Step regDept
    Speak "好的，请问您想挂哪个科室？内科、外科、儿科还是妇科？"
    Listen
    Case "内科" -> goto regDate
    Case "外科" -> goto regDate
    Case "儿科" -> goto regDate
    Case "妇科" -> goto regDate
    Case "ai" -> goto regAI
    Default -> goto regDeptFallback

Step regAI
    AIReply
    goto welcome
'''
    return run_test("医疗脚本测试", test_script, ['module', 'steps'])

def test_ecommerce_script():
    """测试电商脚本片段"""
    test_script = '''
module "ecommerce"

Step buyStart
    Speak "好的，请告诉我想买什么商品？例如：手机、耳机、电脑。"
    Listen
    Case "手机" -> goto buyPhone
    Case "耳机" -> goto buyEarphone
    Case "电脑" -> goto buyLaptop
    Default -> goto buyFallback

Step buyPhone
    Speak "手机库存查询中，请稍候……"
    Lock "phone_stock"
    DBQuery "SELECT stock FROM goods WHERE name='phone'" -> goto outOfStockPhone stock
    If stock <= 0 -> goto outOfStockPhone
    Speak "手机有库存。请问要买几台？"
    Listen assign quantity
    DBExec "UPDATE goods SET stock = stock - {quantity} WHERE name='phone'"
    Unlock "phone_stock"
    Speak "下单成功！您购买了{quantity}台手机。"
    goto welcome

Step outOfStockPhone
    Unlock "phone_stock"
    Speak "抱歉，手机目前缺货。要看看其他商品吗？"
    goto buyStart
'''
    return run_test("电商脚本测试", test_script, ['module', 'steps'])

def test_edge_cases():
    """测试边界情况"""
    test_script = '''
module "边界测试"

Step minimal_step
    Speak "最小步骤"
    Exit

Step complex_conditions
    Listen assign input_var
    If input_var == 10 -> goto number_case
    If input_var == "hello" -> goto string_case  
    If input_var == var2 -> goto variable_case
    If input_var <= 100 -> goto less_equal
    If input_var >= 50 -> goto greater_equal
    Default -> goto fallback

Step number_case
    Speak "数字情况"
    goto complex_conditions

Step string_case
    Speak "字符串情况"
    goto complex_conditions

Step variable_case
    Speak "变量情况"
    goto complex_conditions

Step less_equal
    Speak "小于等于情况"
    goto complex_conditions

Step greater_equal
    Speak "大于等于情况"
    goto complex_conditions

Step fallback
    Speak "默认情况"
    goto complex_conditions
'''
    return run_test("边界情况测试", test_script, ['module', 'steps'])

def save_test_results(results, filename):
    """保存测试结果到文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n测试结果已保存到: {filename}")
    except Exception as e:
        print(f"保存测试结果失败: {e}")

def main():
    """运行所有测试"""
    print("开始DSL解析器测试")
    print("测试PLY-based解析器的各种语法功能")
    
    all_results = {}
    
    # 运行各个测试
    all_results['basic'] = test_basic_syntax()
    all_results['advanced'] = test_advanced_features()
    all_results['medical'] = test_medical_script()
    all_results['ecommerce'] = test_ecommerce_script()
    all_results['edge_cases'] = test_edge_cases()
    
    # 统计测试结果
    successful_tests = sum(1 for result in all_results.values() if result is not None)
    total_tests = len(all_results)
    
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"总测试数: {total_tests}")
    print(f"成功数: {successful_tests}")
    print(f"失败数: {total_tests - successful_tests}")
    
    if successful_tests == total_tests:
        print("所有测试都通过!")
    else:
        print("部分测试失败，请检查错误信息")
    
    # 保存详细结果
    save_test_results(all_results, "parser_test_results.json")
    
    return successful_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)