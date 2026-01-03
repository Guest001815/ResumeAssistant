"""
重启服务器并测试
"""
import subprocess
import time
import sys

print("正在测试（服务器应该已经在运行）...")
print("如果测试失败，请手动重启服务器（Ctrl+C 然后重新运行）")
print()

# 等待一下确保服务器已经加载最新代码
time.sleep(2)

# 运行测试
result = subprocess.run([sys.executable, "test_guide_debug.py"], capture_output=False)
sys.exit(result.returncode)

