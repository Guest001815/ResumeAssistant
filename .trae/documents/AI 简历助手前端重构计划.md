# 升级版重构方案：极致丝滑体验 (Gemini-like)

感谢反馈！根据您的核心指示，我更新了技术方案，重点引入 `framer-motion` 实现“共享元素过渡”，并强化排版与移动端体验。

## 1. 核心依赖升级
- **安装 `framer-motion`**: 这是 React 生态中实现复杂布局动画（Layout Animations）的最佳实践，将用于实现您要求的“输入框平滑位移”效果。

## 2. 动画与交互策略 (Animation Strategy)

### A. 共享元素过渡 (Shared Element Transition)
我们将利用 `framer-motion` 的 `layoutId` 属性连接两个不同页面的 DOM 元素：
- **Landing 页**: 位于屏幕中央的 JD 输入框容器设置 `layoutId="chat-input-area"`。
- **Workspace 页**: 位于左下角的聊天输入框容器设置 **相同** 的 `layoutId="chat-input-area"`。
- **效果**: 当状态切换时，React 会自动计算两个位置的差值，产生一个连贯的、物理移动的视觉效果，而不是生硬的跳变。

### B. 进场动画
- **简历纸张**: 使用 `initial={{ opacity: 0, y: 40 }}` 和 `animate={{ opacity: 1, y: 0 }}`，实现优雅的“上浮淡入”效果。
- **延迟**: 设置轻微的 `delay`，让输入框先就位，纸张随后展开，增加层次感。

### C. 自动触发对话
- **数据流**: 在 Landing 页点击“开始”时，将 JD 和简历内容打包。
- **初始化**: Workspace 加载时，`Chat` 组件会自动接收这些初始数据，并作为第一条 User Message 立即触发 API 调用。

## 3. 视觉与排版 (Visuals & Typography)

### A. 简历纸张 (Resume Paper)
- **尺寸约束**: 严格执行 A4 物理尺寸模拟。
  - `max-w-[210mm]` (A4 宽度)
  - `min-h-[297mm]` (A4 高度)
  - `mx-auto` (水平居中)
  - `shadow-2xl` (悬浮质感阴影)
- **排版引擎**: 启用 `@tailwindcss/typography`。
  - 使用 `prose prose-slate max-w-none` 类名。
  - 针对简历场景微调 `prose-headings` (间距紧凑) 和 `prose-p` (清晰易读)。

### B. 移动端视口适配
- **视口单位**: 全局容器使用 `min-h-[100dvh]` (Dynamic Viewport Height)，完美解决 iOS Safari 地址栏和键盘遮挡问题。

## 4. 组件架构调整

1.  **`LandingPage`**:
    - 包含 `motion.div` 包装的输入区域。
    - 负责收集 JD 和文件。
2.  **`WorkspaceLayout`**:
    - 包含 `motion.div` 包装的 Chat 区域（承接 layoutId）。
    - 包含 `motion.div` 包装的 Resume 区域（进场动画）。
3.  **`ChatPanel`**:
    - 接收 `initialPrompt` 属性，用于自动发送首条指令。

## 5. 执行步骤
1.  安装 `framer-motion`。
2.  创建 `LandingPage` 组件（含动画标记）。
3.  重构 `App.tsx` 为主控中心，处理状态切换与数据传递。
4.  重构 `Chat` 和 `MarkdownPane/ResumePreview` 以适配新布局与排版。
5.  清理旧代码与无用组件。

请确认此方案，我们将开始打造丝滑的 UI 体验。