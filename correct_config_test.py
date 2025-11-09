import os
import subprocess
import time
import platform

# 获取正确的配置文件路径（从源代码复制）
def get_config_path() -> str:
    """获取配置文件的正确路径（跨平台）"""
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")), 
                           "PyTerminal", "config.ini")
    else:
        return os.path.join(os.path.expanduser("~"), ".pyterminal_config.ini")

def test_config_file_generation():
    """测试配置文件生成功能"""
    print("🔍 测试配置文件生成功能...")
    
    # 获取正确的配置文件路径
    config_path = get_config_path()
    print(f"  配置文件路径: {config_path}")
    
    # 清理旧的配置文件（如果存在）
    if os.path.exists(config_path):
        os.remove(config_path)
        print(f"  ✅ 清理了旧的配置文件")
    
    # 确保目录存在（通常由应用程序创建）
    config_dir = os.path.dirname(config_path)
    print(f"  配置目录: {config_dir}")
    if not os.path.exists(config_dir):
        print(f"  配置目录不存在: {config_dir}")
    
    # 运行终端程序生成配置文件
    print("  正在运行终端程序生成配置文件...")
    try:
        process = subprocess.Popen(["python", "python_terminal.py"],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        # 等待程序初始化
        time.sleep(2)
        
        # 优雅终止程序
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # 检查配置文件是否生成
        if os.path.exists(config_path):
            print(f"  ✅ 配置文件生成成功: {config_path}")
            file_size = os.path.getsize(config_path)
            print(f"  ✅ 配置文件大小: {file_size} 字节")
            # 读取并显示前几行内容
            with open(config_path, 'r', encoding='utf-8') as f:
                first_lines = f.readlines()[:5]
            print(f"  ✅ 配置文件内容预览:")
            for line in first_lines:
                print(f"    {line.strip()}")
            return True
        else:
            print(f"  ❌ 配置文件生成失败，文件不存在")
            # 尝试查找可能的配置文件
            print("  尝试查找其他可能的配置文件位置...")
            # 检查用户目录
            user_dir = os.path.expanduser("~")
            print(f"  检查用户目录: {user_dir}")
            for file in os.listdir(user_dir):
                if file.startswith(".pyterminal") or file.startswith("python_terminal"):
                    print(f"    发现: {file}")
            return False
            
    except Exception as e:
        print(f"  ❌ 生成配置文件时出错: {e}")
        return False

if __name__ == "__main__":
    result = test_config_file_generation()
    print(f"\n测试结果: {'成功' if result else '失败'}")