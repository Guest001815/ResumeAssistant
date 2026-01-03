# 简历数据 Schema

## 数据模型
- 顶层结构：`Resume = { basics?: Basics; sections?: Section[] }`（d:\ResumeAssistant\web\src\utils\renderResume.ts:29-32）
- `Basics`：`name?`、`email?`、`phone?`、`location?`（d:\ResumeAssistant\web\src\utils\renderResume.ts:1-6）
- `Section` 联合类型（d:\ResumeAssistant\web\src\utils\renderResume.ts:24-28）
  - `experience`：`title?`、`items?: ExperienceItem[]`
    - `ExperienceItem`：`organization?`、`title?`、`date_start?`、`date_end?`、`location?`、`highlights?: string[]`（d:\ResumeAssistant\web\src\utils\renderResume.ts:8-15）
  - `generic`：`title?`、`items?: GenericItem[]`
    - `GenericItem`：`title?`、`subtitle?`、`date?`、`description?`（d:\ResumeAssistant\web\src\utils\renderResume.ts:17-22）
  - `text`：`title?`、`content?: string`

## 渲染规则
- 头部信息：`name`、`phone`、`email`、`location`（d:\ResumeAssistant\web\src\utils\renderResume.ts:50-55）
- `experience` 渲染：
  - 标题 + 列表项，含职位名、时间范围、地点与要点（d:\ResumeAssistant\web\src\utils\renderResume.ts:61-77,78-84）
- `generic` 渲染：
  - 标题 + 列表项，含标题、日期、副标题、描述（d:\ResumeAssistant\web\src\utils\renderResume.ts:85-99,100-105）
- `text` 渲染：
  - 标题 + 富文本描述（d:\ResumeAssistant\web\src\utils\renderResume.ts:105-115）
- 样式：内联 `<style>` 控制整体排版与色彩（d:\ResumeAssistant\web\src\utils\renderResume.ts:117-134）
- 输出：完整 HTML 文档（d:\ResumeAssistant\web\src\utils\renderResume.ts:135-153）

## 安全转义
- 所有输出字段通过 `esc` 做 HTML 转义，避免 XSS（d:\ResumeAssistant\web\src\utils\renderResume.ts:34-41）

## 示例
```json
{
  "basics": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "phone": "13800000000",
    "location": "北京"
  },
  "sections": [
    {
      "type": "experience",
      "title": "工作经历",
      "items": [
        {
          "organization": "示例科技",
          "title": "前端工程师",
          "date_start": "2021-01",
          "date_end": "2023-06",
          "location": "北京",
          "highlights": [
            "主导组件库与文档平台搭建",
            "推进前端工程化与性能优化"
          ]
        }
      ]
    },
    {
      "type": "generic",
      "title": "教育经历",
      "items": [
        {
          "title": "计算机科学本科",
          "subtitle": "某大学",
          "date": "2016-2020",
          "description": "数据结构、算法与软件工程相关课程"
        }
      ]
    },
    {
      "type": "text",
      "title": "自我评价",
      "content": "关注可维护性与用户体验，热爱开源与知识分享。"
    }
  ]
}
```

## 扩展建议
- 模板化：将内联样式抽象为可切换模板与主题。
- 校验：为 `Resume` 增加类型校验与必填项提示。

## Markdown 映射
- 目的：从结构化 `Resume` 生成可读的 Markdown 文本，方便编辑与分享。
- 生成器：`resumeToMarkdown(resume)`（d:\ResumeAssistant\web\src\utils\markdown.ts:138-193）。
- 规则概要：
  - 顶部头部：`# {name}`，下一行拼接 `电话/邮箱/地址`，空行分隔。
  - `experience`：每项使用 `**组织 - 职位** (起止日期)`，下一行斜体 `_地点_`，随后按 `- 要点` 列出 `highlights`（d:\ResumeAssistant\web\src\utils\markdown.ts:165-175）。
  - `generic`：`**标题 (日期)**`，下一行斜体 `_副标题_`，再下一行描述文本（d:\ResumeAssistant\web\src\utils\markdown.ts:178-185）。
  - `text`：直接输出内容段落（d:\ResumeAssistant\web\src\utils\markdown.ts:186-190）。
- 文本整洁：所有拼接项会 `trim` 并过滤空白，避免多余空格（d:\ResumeAssistant\web\src\utils\markdown.ts:144-149）。
- 安全性：仅做最小必要的值转换，不注入额外标记，避免破坏编辑体验。
