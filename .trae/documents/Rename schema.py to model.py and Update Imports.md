我将把 `backend/schema.py` 重命名为 `backend/model.py`，并更新所有相关的引用。

**重命名文件:**

* 将 `c:\Users\admin\Desktop\ResumeAssistant\backend\schema.py` 重命名为 `c:\Users\admin\Desktop\ResumeAssistant\backend\model.py`。

**更新导入语句:**
我将更新以下文件，使其从 `model` 而不是 `schema` 导入：

1. **`backend/plan_agent.py`**

   * 将 `from schema import Resume, TaskList` 改为 `from model import Resume, TaskList`

   * 将 `from schema import Resume` 改为 `from model import Resume`

2. **`backend/parse_resume.py`**

   * 将 `from schema import Resume` 改为 `from model import Resume`

   * 将 `from backend.schema import Resume` 改为 `from backend.model import Resume`

   * 更新提到 'schema' 的错误信息。

3. **`backend/api.py`**

   * 将 `from schema import Resume` 改为 `from model import Resume`

4. **`backend/editor_agent.py`**

   * 将 `from schema import Resume` 改为 `from model import Resume`

5. **`backend/tool_framework.py`**

   * 将 `from schema import Resume, ExperienceSection, ExperienceItem, GenericSection, GenericItem, ToolMessage` 改为 `from model import Resume, ExperienceSection, ExperienceItem, GenericSection, GenericItem, ToolMessage`

