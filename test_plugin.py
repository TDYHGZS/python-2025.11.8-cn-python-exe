#!/usr/bin/env python3
# 简单的测试脚本，验证插件化架构
import os
import sys
import subprocess

# 测试help命令
print("测试help命令:")
result = subprocess.run(["python", "python_terminal.py", "-c", "help"], 
                       capture_output=True, text=True, timeout=10)
print(f"返回码: {result.returncode}")
print(f"输出:\n{result.stdout}")
print(f"错误:\n{result.stderr}")

print("\n" + "="*50 + "\n")

# 测试dir命令
print("测试dir命令:")
result = subprocess.run(["python", "python_terminal.py", "-c", "dir"], 
                       capture_output=True, text=True, timeout=10)
print(f"返回码: {result.returncode}")
print(f"输出:\n{result.stdout}")
print(f"错误:\n{result.stderr}")

print("\n" + "="*50 + "\n")

# 测试pwd命令
print("测试pwd命令:")
result = subprocess.run(["python", "python_terminal.py", "-c", "pwd"], 
                       capture_output=True, text=True, timeout=10)
print(f"返回码: {result.returncode}")
print(f"输出:\n{result.stdout}")
print(f"错误:\n{result.stderr}")

print("\n" + "="*50 + "\n")

# 测试插件化架构 - 检查配置文件
print("检查配置文件是否生成:")
if os.path.exists(os.path.join(os.environ.get("APPDATA", ""), "PyTerminal", "config.ini")):
    print("✓ 配置文件已成功生成！")
else:
    print("✗ 配置文件未生成")