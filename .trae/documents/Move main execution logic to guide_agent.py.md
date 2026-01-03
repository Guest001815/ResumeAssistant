我将把 `backend/main.py` 中的 `main` 执行逻辑合并到 `backend/guide_agent.py` 文件底部，以便您直接通过运行 `guide_agent.py` 进行测试。

### 1. 更新 `backend/guide_agent.py`
我会将 `backend/main.py` 的内容追加到 `backend/guide_agent.py` 的末尾。
- **调整导入**：由于代码在同一个文件中，我会移除 `from guide_agent import GuideAgent` 这一行。
- **添加测试入口**：将 `main()` 函数和 `if __name__ == "__main__":` 代码块放置在文件底部。

### 2. 清理文件
在确认迁移完成后，我会删除不再需要的 `backend/main.py` 文件。

这样，您就可以直接使用 `python guide_agent.py` 来启动测试了。