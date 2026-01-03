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
 * 智能格式化文本：识别段落、列表、换行等层级结构
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
    
    const lines = trimmed.split('\n').map(l => l.trim()).filter(l => l);
    
    // 检测是否为数字列表（如 "1. xxx", "2. xxx"）
    const isNumberedList = lines.length > 1 && lines.every(line => /^\d+\.\s+/.test(line));
    if (isNumberedList) {
      const items = lines.map(line => {
        const content = line.replace(/^\d+\.\s+/, '');
        return `<li>${inlineMd(content)}</li>`;
      }).join('');
      formattedParagraphs.push(`<ol>${items}</ol>`);
      continue;
    }
    
    // 检测是否为无序列表（如 "- xxx" 或 "• xxx"）
    const isBulletList = lines.length > 1 && lines.every(line => /^[-•]\s+/.test(line));
    if (isBulletList) {
      const items = lines.map(line => {
        const content = line.replace(/^[-•]\s+/, '');
        return `<li>${inlineMd(content)}</li>`;
      }).join('');
      formattedParagraphs.push(`<ul>${items}</ul>`);
      continue;
    }
    
    // 普通段落：单行或多行用 <br> 连接
    if (lines.length === 1) {
      formattedParagraphs.push(`<p>${inlineMd(lines[0])}</p>`);
    } else {
      const content = lines.map(inlineMd).join('<br>');
      formattedParagraphs.push(`<p>${content}</p>`);
    }
  }
  
  return formattedParagraphs.join('');
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
