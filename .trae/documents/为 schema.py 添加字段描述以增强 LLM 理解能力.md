我将为 `backend/schema.py` 中的 Pydantic 模型添加详细的字段描述 (Field descriptions)，以便大模型能更好地理解简历的数据结构。

以下是具体的修改计划：

### 1. 修改 `GenericItem`
为通用条目添加描述，用于教育背景、项目经历等通用列表项。
- `id`: 唯一标识符
- `title`: 标题（如学校名、项目名）
- `subtitle`: 副标题（如专业、学位）
- `date`: 时间段
- `description`: 详细说明

### 2. 修改 `ExperienceItem`
为经历条目添加描述，专门用于工作经历。
- `id`: 唯一标识符
- `title`: 职位/角色
- `organization`: 公司/组织名称
- `date_start`: 开始时间
- `date_end`: 结束时间
- `location`: 地点
- `highlights`: 工作亮点/成就列表

### 3. 修改 `SectionBase` 及其子类
为章节基类及具体章节类型添加描述。
- `SectionBase.id`: 章节唯一标识符
- `SectionBase.title`: 章节标题
- `ExperienceSection.items`: 工作经历列表
- `GenericSection.items`: 通用项目列表
- `TextSection.content`: 纯文本内容（用于自我评价等）

### 4. 修改 `Basics`
为基本信息添加描述。
- `name`: 姓名
- `label`: 职位/头衔
- `email`: 邮箱
- `phone`: 电话
- `links`: 链接列表

### 5. 修改 `Resume`
为简历主体添加描述。
- `basics`: 基础信息部分
- `sections`: 简历章节列表

所有字段将使用 `Field(..., description="...")` 的形式进行注解。