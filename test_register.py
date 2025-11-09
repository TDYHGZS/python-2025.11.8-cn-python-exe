#!/usr/bin/env python3
# 测试插件化命令注册功能

import os
import sys
import subprocess

def test_help_command():
    """测试help命令是否能正常工作"""
    print("测试help命令...")
    # 捕获输出并显示
    result = subprocess.run(["python", "python_terminal.py", "-c", "help"], 
                           capture_output=True, text=True, timeout=10)
    print(f"返回码: {result.returncode}")
    print(f"\n标准输出:\n{result.stdout}")
    print(f"\n错误输出:\n{result.stderr}")
    return result.stdout

def test_pwd_command():
    """测试pwd命令是否能正常工作"""
    print("\n测试pwd命令...")
    result = subprocess.run(["python", "python_terminal.py", "-c", "pwd"], 
                           capture_output=True, text=True, timeout=10)
    print(f"返回码: {result.returncode}")
    print(f"\n标准输出:\n{result.stdout}")
    print(f"\n错误输出:\n{result.stderr}")
    return result.stdout

def test_config_file():
    """检查配置文件是否生成"""
    print("\n检查配置文件是否生成...")
    if sys.platform == "win32":
        config_dir = os.path.join(os.environ.get("APPDATA", ""), "PyTerminal")
        config_path = os.path.join(config_dir, "config.ini")
    else:
        config_path = os.path.join(os.path.expanduser("~"), ".pyterminal_config.ini")
    
    if os.path.exists(config_path):
        print(f"✅ 配置文件存在: {config_path}")
        # 读取并显示配置文件内容
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print("\n配置文件内容:")
                print("=" * 50)
                print(content)
                print("=" * 50)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
    else:
        print(f"❌ 配置文件不存在: {config_path}")
        print(f"  配置目录: {config_dir}")
        print(f"  目录是否存在: {os.path.exists(config_dir)}")

if __name__ == "__main__":
    print("开始测试插件化命令注册功能...")
    print("=" * 50)
    
    # 先尝试创建配置目录（避免权限问题）
    if sys.platform == "win32":
        config_dir = os.path.join(os.environ.get("APPDATA", ""), "PyTerminal")
        try:
            os.makedirs(config_dir, exist_ok=True)
            print(f"已创建配置目录: {config_dir}")
        except Exception as e:
            print(f"创建配置目录失败: {e}")
    
    # 测试基本命令
    help_output = test_help_command()
    pwd_output = test_pwd_command()
    
    # 检查配置文件
    test_config_file()
    
    print("\n" + "=" * 50)
    print("测试完成！")