#!/usr/bin/env python3
"""
电商流程调试测试
"""

import sys
import os
import sqlite3

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))  # tests目录
project_root = os.path.dirname(current_dir)  # medical_dsl目录
src_dir = os.path.join(project_root, "src")
database_dir = os.path.join(project_root, "database")

sys.path.insert(0, src_dir)

from test_stubs import MockDSLParser, MockLLMClient
from interpreter import DSLInterpreter

def debug_database():
    """直接测试数据库连接和查询"""
    print("🔧 直接测试数据库连接和查询")
    
    db_path = os.path.join(database_dir, "ecommerce.db")
    print(f"数据库路径: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        print("数据库连接成功")
        
        cursor = conn.cursor()
        
        # 测试查询
        query = "SELECT stock FROM goods WHERE name='phone'"
        print(f"执行查询: {query}")
        
        cursor.execute(query)
        result = cursor.fetchone()
        
        print(f"查询结果: {result}")
        if result:
            print(f"手机库存: {result[0]}")
        
        conn.close()
        print("数据库测试完成")
        return True
        
    except Exception as e:
        print(f"数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_ecommerce_flow():
    """调试电商流程"""
    print("\n调试电商流程")
    
    # 创建解释器
    script_ast = MockDSLParser.create_ecommerce_script()
    db_path = os.path.join(database_dir, "ecommerce.db")
    
    print(f"创建解释器，数据库路径: {db_path}")
    interpreter = DSLInterpreter(script_ast, MockLLMClient(), db_path)
    
    # 设置当前步骤为 buyPhone
    interpreter.current_step = "buyPhone"
    
    print(f"当前步骤: {interpreter.current_step}")
    
    # 手动执行 buyPhone 步骤
    try:
        interpreter._execute_current_step()
        print("buyPhone 步骤执行成功")
        print(f"变量状态: {interpreter.variables}")
        print(f"下一个步骤: {interpreter.current_step}")
    except Exception as e:
        print(f"buyPhone 步骤执行失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主调试函数"""
    print("开始电商流程调试")
    
    # 1. 测试数据库连接
    if not debug_database():
        return
    
    print("\n" + "="*50)
    
    # 2. 调试电商流程
    debug_ecommerce_flow()

if __name__ == "__main__":
    main()