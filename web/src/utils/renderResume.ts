type Basics = {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
};

type ExperienceItem = {
  organization?: string;
  title?: string;
  date_start?: string;
  date_end?: string;
  location?: string;
  highlights?: string[];
};

type GenericItem = {
  title?: string;
  subtitle?: string;
  date?: string;
  description?: string;
};

type Section =
  | { type: "experience"; title?: string; items?: ExperienceItem[] }
  | { type: "generic"; title?: string; items?: GenericItem[] }
  | { type: "text"; title?: string; content?: string };

type Resume = {
  basics?: Basics;
  sections?: Section[];
};

function esc(x: any) {
  if (x === null || x === undefined) return "";
  return String(x)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;");
}

/**
 * 处理行内Markdown格式：**加粗**、*斜体*、`代码`
 * @param s 原始文本
 * @returns 转换后的HTML字符串
 */
function inlineMd(s: string): string {
  let t = esc(s);
  // 加粗: **text** 或 __text__
  t = t.replace(/(\*\*|__)(.*?)\1/g, (_m, _d, inner) => `<strong>${inner}</strong>`);
  // 斜体: *text* 或 _text_
  t = t.replace(/(\*|_)(.*?)\1/g, (_m, _d, inner) => `<em>${inner}</em>`);
  // 行内代码: `code`
  t = t.replace(/`([^`]+)`/g, (_m, code) => `<code>${code}</code>`);
  return t;
}

/**
 * 检测一行是否为 bullet point（支持前导空格）
 * @param line 原始行文本
 * @returns 是否为 bullet point
 */
function isBulletLine(line: string): boolean {
  return /^\s*[-•·]\s*/.test(line);
}

/**
 * 检测一行是否为数字列表项（支持前导空格）
 * @param line 原始行文本
 * @returns 是否为数字列表项
 */
function isNumberedLine(line: string): boolean {
  return /^\s*\d+\.\s+/.test(line);
}

/**
 * 智能格式化文本：识别段落、列表、换行等层级结构
 * 支持嵌套列表和缩进的子项
 * @param text 原始文本（可能包含 \n 换行符）
 * @returns 格式化后的 HTML 字符串
 */
function formatText(text: string): string {
  if (!text) return "";
  
  // 按双换行符分段
  const paragraphs = text.split(/\n\n+/);
  const formattedParagraphs: string[] = [];
  
  for (const para of paragraphs) {
    const trimmed = para.trim();
    if (!trimmed) continue;
    
    // 保留原始行（不 trim），用于检测缩进
    const rawLines = trimmed.split('\n').filter(l => l.trim());
    
    if (rawLines.length === 0) continue;
    
    // 检测是否为数字列表：第一行是数字列表项，或者大部分行是数字列表项
    const numberedCount = rawLines.filter(isNumberedLine).length;
    const isNumberedList = numberedCount > 0 && numberedCount >= rawLines.length * 0.5;
    
    if (isNumberedList) {
      const items = parseListItems(rawLines, 'numbered');
      formattedParagraphs.push(`<ol>${items}</ol>`);
      continue;
    }
    
    // 检测是否为无序列表：第一行是 bullet，或者大部分行是 bullet
    const bulletCount = rawLines.filter(isBulletLine).length;
    const isBulletList = bulletCount > 0 && (
      isBulletLine(rawLines[0]) || // 第一行是 bullet
      bulletCount >= rawLines.length * 0.5 // 或者至少一半的行是 bullet
    );
    
    if (isBulletList) {
      const items = parseListItems(rawLines, 'bullet');
      formattedParagraphs.push(`<ul>${items}</ul>`);
      continue;
    }
    
    // 普通段落：单行或多行用 <br> 连接
    const lines = rawLines.map(l => l.trim());
    if (lines.length === 1) {
      formattedParagraphs.push(`<p>${inlineMd(lines[0])}</p>`);
    } else {
      const content = lines.map(inlineMd).join('<br>');
      formattedParagraphs.push(`<p>${content}</p>`);
    }
  }
  
  return formattedParagraphs.join('');
}

/**
 * 解析列表项，支持嵌套结构
 * 将连续的缩进行合并到前一个列表项中
 * @param lines 原始行数组
 * @param type 列表类型
 * @returns HTML 列表项字符串
 */
function parseListItems(lines: string[], type: 'bullet' | 'numbered'): string {
  const result: string[] = [];
  let currentItem: string[] = [];
  
  const isListLine = type === 'bullet' ? isBulletLine : isNumberedLine;
  const stripPrefix = type === 'bullet' 
    ? (s: string) => s.replace(/^\s*[-•·]\s*/, '')
    : (s: string) => s.replace(/^\s*\d+\.\s+/, '');
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    if (isListLine(line)) {
      // 如果有之前累积的内容，先输出
      if (currentItem.length > 0) {
        result.push(formatListItem(currentItem));
        currentItem = [];
      }
      // 开始新的列表项
      currentItem.push(stripPrefix(trimmedLine));
    } else {
      // 非列表行：作为前一个列表项的延续内容
      if (currentItem.length > 0) {
        // 检测是否为子级 bullet（缩进的 - 开头）
        if (/^\s+[-•·]\s*/.test(line)) {
          // 子级列表项，保留并作为延续内容
          currentItem.push(trimmedLine.replace(/^[-•·]\s*/, ''));
        } else {
          // 普通延续内容
          currentItem.push(trimmedLine);
        }
      } else {
        // 没有前一个列表项，单独作为一个项
        currentItem.push(trimmedLine);
      }
    }
  }
  
  // 处理最后一个列表项
  if (currentItem.length > 0) {
    result.push(formatListItem(currentItem));
  }
  
  return result.join('');
}

/**
 * 格式化单个列表项
 * @param lines 列表项的内容行数组
 * @returns HTML <li> 元素
 */
function formatListItem(lines: string[]): string {
  if (lines.length === 1) {
    return `<li>${inlineMd(lines[0])}</li>`;
  }
  // 多行内容用 <br> 连接
  const content = lines.map(inlineMd).join('<br>');
  return `<li>${content}</li>`;
}

export function renderResumeHtmlFromSchema(resume: Resume): string {
  const basics = resume?.basics || {};
  const name = basics.name || "";
  const phone = basics.phone || "";
  const email = basics.email || "";
  const location = basics.location || "";
  const sections = resume?.sections || [];
  const headerHtml = `
    <div class="header">
      <div class="name">${esc(name)}</div>
      <div class="contact-info">电话: ${esc(phone)} | 邮箱: ${esc(email)} | 地址: ${esc(location)}</div>
    </div>
  `;
  const bodySections: string[] = [];
  for (const sec of sections) {
    const stype = (sec as any).type;
    const stitle = esc((sec as any).title);
    if (stype === "experience") {
      const items = (sec as any).items || [];
      const itemsHtml: string[] = [];
      for (const it of items) {
        const highlights = (it.highlights || []).map((h: string) => `<li>${formatText(h)}</li>`).join("");
        itemsHtml.push(`
          <div class="item">
            <div class="item-header">
              <span class="item-title">${esc(it.organization)} - ${esc(it.title)}</span>
              <span class="item-date">${esc(it.date_start)} - ${esc(it.date_end)}</span>
            </div>
            <div class="item-subtitle">${esc(it.location)}</div>
            <div class="item-description">
              <ul>${highlights}</ul>
            </div>
          </div>
        `);
      }
      bodySections.push(`
        <div class="section">
          <div class="section-title">${stitle}</div>
          ${itemsHtml.join("")}
        </div>
      `);
    } else if (stype === "generic") {
      const items = (sec as any).items || [];
      const itemsHtml: string[] = [];
      
      // 检测是否为技能类型的 section（需要强制使用紧凑布局）
      const skillKeywords = ["技能", "技术", "专长", "技术栈", "工具"];
      const isSkillSection = skillKeywords.some(kw => stitle.includes(kw));
      
      // 检测是否为紧凑型section（如技能、荣誉）
      // 判断标准：
      // 1. 技能类型的 section 强制使用紧凑布局
      // 2. 或者：大部分项目没有长 description 且 items 数量大于 3
      const hasLongDescriptions = items.some((it: any) => 
        it.description && it.description.length > 100
      );
      
      // 技能类型强制紧凑布局，或满足原有条件
      if (isSkillSection || (!hasLongDescriptions && items.length > 3)) {
        // 使用紧凑布局（适合技能、荣誉等）
        for (const it of items) {
          const subtitle = it.subtitle ? `<span class="compact-subtitle">${esc(it.subtitle)}</span>` : '';
          itemsHtml.push(`
            <div class="compact-item">
              <span class="compact-bullet">•</span>
              <span class="compact-title">${esc(it.title)}</span>
              ${subtitle}
            </div>
          `);
        }
        bodySections.push(`
          <div class="section">
            <div class="section-title">${stitle}</div>
            <div class="compact-grid">
              ${itemsHtml.join("")}
            </div>
          </div>
        `);
      } else {
        // 使用标准布局（适合项目经历等）
        for (const it of items) {
          itemsHtml.push(`
            <div class="item">
              <div class="item-header">
                <span class="item-title">${esc(it.title)}</span>
                <span class="item-date">${esc(it.date)}</span>
              </div>
              <div class="item-subtitle">${esc(it.subtitle)}</div>
              <div class="item-description">${formatText(it.description || "")}</div>
            </div>
          `);
        }
        bodySections.push(`
          <div class="section">
            <div class="section-title">${stitle}</div>
            ${itemsHtml.join("")}
          </div>
        `);
      }
    } else if (stype === "text") {
      const content = formatText((sec as any).content || "");
      bodySections.push(`
        <div class="section">
          <div class="section-title">${stitle}</div>
          <div class="item">
            <div class="item-description">${content}</div>
          </div>
        </div>
      `);
    }
  }
  const style = `
    <style>
      body { margin: 0; padding: 0; font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #fff; }
      .resume-container { width: 100%; box-sizing: border-box; padding: 40px; }
      .header { text-align: center; border-bottom: 2px solid #0066cc; padding-bottom: 20px; margin-bottom: 30px; page-break-after: avoid; break-after: avoid; page-break-inside: avoid; break-inside: avoid; }
      .name { font-size: 28px; font-weight: bold; color: #0066cc; margin-bottom: 10px; }
      .contact-info { font-size: 13px; color: #666; margin-bottom: 5px; }
      .section { margin-bottom: 25px; page-break-inside: avoid; break-inside: avoid; page-break-before: auto; break-before: auto; }
      .section-title { font-size: 16px; font-weight: bold; color: #0066cc; border-left: 4px solid #0066cc; padding-left: 12px; margin-bottom: 15px; page-break-after: avoid; break-after: avoid; }
      .item { margin-bottom: 15px; page-break-inside: avoid; break-inside: avoid; }
      .item-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
      .item-title { font-weight: bold; color: #333; }
      .item-date { color: #999; font-size: 13px; }
      .item-subtitle { color: #666; font-size: 13px; margin-bottom: 5px; }
      .item-description { color: #555; font-size: 13px; line-height: 1.5; margin-left: 10px; }
      .item-description ul { padding-left: 20px; margin: 5px 0; }
      .item-description ol { padding-left: 20px; margin: 5px 0; }
      .item-description li { margin-bottom: 8px; }
      .item-description p { margin: 8px 0; line-height: 1.6; }
      .item-description p:first-child { margin-top: 0; }
      .item-description p:last-child { margin-bottom: 0; }
      .item-description li p { margin: 4px 0; }
      .item-description li p:first-child { margin-top: 0; }
      .item-description li p:last-child { margin-bottom: 0; }
      
      /* 紧凑型布局样式（用于技能、荣誉等） */
      .compact-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px 16px; margin-left: 10px; page-break-inside: avoid; break-inside: avoid; }
      .compact-item { display: flex; align-items: baseline; gap: 6px; font-size: 13px; line-height: 1.6; page-break-inside: avoid; break-inside: avoid; }
      .compact-bullet { color: #0066cc; font-weight: bold; flex-shrink: 0; }
      .compact-title { color: #333; font-weight: 500; }
      .compact-subtitle { color: #666; font-size: 12px; margin-left: 4px; }
      .compact-subtitle::before { content: "("; }
      .compact-subtitle::after { content: ")"; }
      
      @media print {
        body { -webkit-print-color-adjust: exact; }
        .resume-container { padding: 0; }
        .compact-grid { grid-template-columns: repeat(2, 1fr); }
      }
    </style>
  `;
  const html = `
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>个人简历</title>
      ${style}
    </head>
    <body>
      <div class="resume-container">
        ${headerHtml}
        ${bodySections.join("")}
      </div>
    </body>
    </html>
  `;
  return html;
}
