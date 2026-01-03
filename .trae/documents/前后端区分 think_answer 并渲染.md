## 后端调整
- 在 `backend/editor_agent.py` 将内容增量改为 `answer` 类型：
  - 保持推理内容 `reasoning_content` 仍以 `think` 类型流出：`backend/editor_agent.py:92`。
  - 将普通文本增量改为 `answer` 类型：把 `backend/editor_agent.py:94` 从 `type: "think"` 改为 `type: "answer"`。
  - 为稳健性，同步将非字典增量分支改为 `answer`：把 `backend/editor_agent.py:97` 从 `type: "think"` 改为 `type: "answer"`。
- 其余事件类型（`tool`、`error`、`data`）保持不变。

## 前端渲染
- 在 `web/src/components/Chat.tsx` 新增对 `answer` 事件的处理与渲染：
  - 添加 `answerText` 状态并在收到 `t === "answer"` 时按流式拼接显示。
  - 保持 `think` 以灰色斜体实时显示，不进入历史。
  - `tool` 与 `error` 仍作为辅助输出实时显示。
- 完成一次流式后：
  - 若存在 `answerText`，将其作为一条 `assistant` 消息追加到历史；否则以 `toolLines.join("\n")` 作为回退内容写入历史。
  - 清空临时的 `thinking` 与 `answerText`。

## 验证要点
- 发起一次对话，应看到两条实时区域：灰色斜体的 `think` 与正常样式的 `answer`；结束后历史中落一条完整的 `assistant` 回答。
- 纯工具调用场景（无 `answer` 增量）历史应落下工具输出的汇总文本。
- 简历更新事件 `data` 仍能刷新右侧预览。

如确认，该计划会按上述文件位置进行最小化改动，并保持现有交互与样式一致。