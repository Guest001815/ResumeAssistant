export function markdownToHtml(md: string): string {
  const esc = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let inCodeBlock = false;
  let listMode: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listMode) {
      out.push(listMode === "ul" ? "</ul>" : "</ol>");
      listMode = null;
    }
  };

  for (let raw of lines) {
    const line = raw.replace(/\t/g, "    ");
    if (line.trim().startsWith("```")) {
      if (!inCodeBlock) {
        flushList();
        inCodeBlock = true;
        out.push("<pre><code>");
      } else {
        inCodeBlock = false;
        out.push("</code></pre>");
      }
      continue;
    }
    if (inCodeBlock) {
      out.push(esc(line) + "\n");
      continue;
    }
    if (/^\s*([-*_]){3,}\s*$/.test(line)) {
      flushList();
      out.push("<hr/>");
      continue;
    }
    const h = line.match(/^(\#{1,6})\s+(.*)$/);
    if (h) {
      flushList();
      const level = h[1].length;
      out.push(`<h${level}>${inlineMd(h[2])}</h${level}>`);
      continue;
    }
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    if (ul) {
      if (listMode !== "ul") {
        flushList();
        listMode = "ul";
        out.push("<ul>");
      }
      out.push(`<li>${inlineMd(ul[1])}</li>`);
      continue;
    }
    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ol) {
      if (listMode !== "ol") {
        flushList();
        listMode = "ol";
        out.push("<ol>");
      }
      out.push(`<li>${inlineMd(ol[1])}</li>`);
      continue;
    }
    const quote = line.match(/^\s*>\s+(.*)$/);
    if (quote) {
      flushList();
      out.push(`<blockquote>${inlineMd(quote[1])}</blockquote>`);
      continue;
    }
    if (line.trim() === "") {
      flushList();
      out.push("");
      continue;
    }
    flushList();
    out.push(`<p>${inlineMd(line)}</p>`);
  }
  flushList();

  const style = `
    <style>
      body { font-family: -apple-system, Segoe UI, Microsoft YaHei, sans-serif; color: #333; line-height: 1.7; background: #f7f7f7; }
      .md-container { max-width: 800px; margin: 20px auto; background: #fff; padding: 24px 28px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
      h1,h2,h3,h4,h5,h6 { color: #0b5fb3; margin: 16px 0 8px; }
      p { margin: 8px 0; }
      ul, ol { margin: 8px 0 8px 20px; }
      li { margin: 4px 0; }
      blockquote { border-left: 4px solid #ddd; margin: 8px 0; padding: 6px 12px; color: #555; background: #fafafa; }
      pre { background: #1e1e1e; color: #ddd; padding: 12px; border-radius: 6px; overflow: auto; }
      code { background: #f0f2f5; padding: 2px 6px; border-radius: 4px; }
      a { color: #0b5fb3; text-decoration: none; }
      a:hover { text-decoration: underline; }
      hr { border: none; border-top: 1px solid #e0e0e0; margin: 12px 0; }
      img { max-width: 100%; border-radius: 4px; }
    </style>
  `;

  const htmlDoc = `
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Markdown 预览</title>
      ${style}
    </head>
    <body>
      <div class="md-container">
        ${out.join("\n")}
      </div>
    </body>
    </html>
  `;
  return htmlDoc;
}

function inlineMd(s: string): string {
  const esc = (x: string) =>
    x
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  let t = esc(s);
  t = t.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_m, alt, url) => `<img alt="${alt}" src="${url}"/>`);
  t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, text, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`);
  t = t.replace(/(\*\*|__)(.*?)\1/g, (_m, _d, inner) => `<strong>${inner}</strong>`);
  t = t.replace(/(\*|_)(.*?)\1/g, (_m, _d, inner) => `<em>${inner}</em>`);
  t = t.replace(/`([^`]+)`/g, (_m, code) => `<code>${code}</code>`);
  return t;
}

/**
 * 将Markdown文本解析为Resume对象
 * @param markdown - Markdown格式的简历文本
 * @returns Resume对象
 * @throws Error 如果解析失败
 */
export function markdownToResume(markdown: string): any {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  let lineIdx = 0;
  
  const resume: any = {
    basics: {
      name: "",
      label: "",
      email: "",
      phone: "",
      location: "",
      links: []
    },
    sections: []
  };

  let sectionIdCounter = 0;
  let itemIdCounter = 0;

  const generateSectionId = () => `section_${++sectionIdCounter}`;
  const generateItemId = () => `item_${++itemIdCounter}`;

  // 解析基本信息（姓名和联系方式）
  while (lineIdx < lines.length) {
    const line = lines[lineIdx].trim();
    
    // 解析姓名 (# 姓名)
    if (line.startsWith("# ")) {
      resume.basics.name = line.substring(2).trim();
      lineIdx++;
      continue;
    }

    // 解析联系方式 (电话: xxx 邮箱: xxx 地址: xxx)
    if (line.includes("电话:") || line.includes("邮箱:") || line.includes("地址:")) {
      const phoneMatch = line.match(/电话:\s*([^\s]+)/);
      const emailMatch = line.match(/邮箱:\s*([^\s]+)/);
      const locationMatch = line.match(/地址:\s*(.+?)(?:电话:|邮箱:|$)/);
      
      if (phoneMatch) resume.basics.phone = phoneMatch[1].trim();
      if (emailMatch) resume.basics.email = emailMatch[1].trim();
      if (locationMatch) resume.basics.location = locationMatch[1].trim();
      lineIdx++;
      continue;
    }

    // 空行跳过
    if (line === "") {
      lineIdx++;
      continue;
    }

    // 遇到## 标题，表示开始section部分
    if (line.startsWith("## ")) {
      break;
    }

    lineIdx++;
  }

  // 解析sections
  while (lineIdx < lines.length) {
    const line = lines[lineIdx].trim();
    
    // 跳过空行
    if (line === "") {
      lineIdx++;
      continue;
    }

    // 解析section标题 (## 标题)
    if (line.startsWith("## ")) {
      const sectionTitle = line.substring(3).trim();
      const section: any = {
        id: generateSectionId(),
        title: sectionTitle,
        type: "text", // 默认类型，后续根据内容判断
        items: [],
        content: ""
      };

      lineIdx++;

      // 收集section内容
      const sectionLines: string[] = [];
      while (lineIdx < lines.length && !lines[lineIdx].trim().startsWith("## ")) {
        sectionLines.push(lines[lineIdx]);
        lineIdx++;
      }

      // 分析section类型和内容
      const sectionContent = sectionLines.join("\n").trim();
      const parsedSection = parseSection(section, sectionContent, generateItemId);
      resume.sections.push(parsedSection);
    } else {
      lineIdx++;
    }
  }

  // 验证必填字段
  if (!resume.basics.name) {
    throw new Error("简历必须包含姓名（# 姓名）");
  }

  return resume;
}

/**
 * 解析section内容，判断类型并提取items
 */
function parseSection(section: any, content: string, generateItemId: () => string): any {
  if (!content.trim()) {
    return { ...section, type: "text", content: "" };
  }

  const lines = content.split("\n");
  const items: any[] = [];
  let currentItem: any = null;
  let highlights: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    if (line === "") {
      // 空行表示一个item结束
      if (currentItem) {
        if (highlights.length > 0) {
          currentItem.highlights = highlights;
          highlights = [];
        }
        items.push(currentItem);
        currentItem = null;
      }
      continue;
    }

    // 检测experience格式: **公司 - 职位** (时间)
    const expMatch = line.match(/^\*\*(.+?)\s*-\s*(.+?)\*\*\s*(?:\((.+?)\))?/);
    if (expMatch) {
      // 保存上一个item
      if (currentItem) {
        if (highlights.length > 0) {
          currentItem.highlights = highlights;
          highlights = [];
        }
        items.push(currentItem);
      }

      // 创建新的experience item
      currentItem = {
        id: generateItemId(),
        organization: expMatch[1].trim(),
        title: expMatch[2].trim(),
        date_start: "",
        date_end: "",
        location: "",
        highlights: []
      };

      // 解析时间
      if (expMatch[3]) {
        const dates = expMatch[3].split("-").map(d => d.trim());
        currentItem.date_start = dates[0] || "";
        currentItem.date_end = dates[1] || dates[0] || "";
      }
      
      section.type = "experience";
      continue;
    }

    // 检测generic格式: **标题** (日期) 或 **标题**
    const genMatch = line.match(/^\*\*(.+?)\*\*\s*(?:\((.+?)\))?/);
    if (genMatch) {
      // 保存上一个item
      if (currentItem) {
        if (highlights.length > 0) {
          currentItem.highlights = highlights;
          highlights = [];
        }
        items.push(currentItem);
      }

      // 创建新的generic item
      currentItem = {
        id: generateItemId(),
        title: genMatch[1].trim(),
        date: genMatch[2] ? genMatch[2].trim() : "",
        subtitle: "",
        description: ""
      };

      if (section.type !== "experience") {
        section.type = "generic";
      }
      continue;
    }

    // 检测斜体（subtitle或location）
    const italicMatch = line.match(/^_(.+?)_$/);
    if (italicMatch && currentItem) {
      if (currentItem.location !== undefined) {
        // experience类型
        currentItem.location = italicMatch[1].trim();
      } else if (currentItem.subtitle !== undefined) {
        // generic类型
        currentItem.subtitle = italicMatch[1].trim();
      }
      continue;
    }

    // 检测列表项（highlights）
    if (line.startsWith("- ")) {
      highlights.push(line.substring(2).trim());
      continue;
    }

    // 普通文本（description）
    if (currentItem && currentItem.description !== undefined) {
      currentItem.description = (currentItem.description ? currentItem.description + " " : "") + line;
    }
  }

  // 保存最后一个item
  if (currentItem) {
    if (highlights.length > 0) {
      currentItem.highlights = highlights;
    }
    items.push(currentItem);
  }

  // 如果解析到了items，返回对应类型的section
  if (items.length > 0) {
    if (section.type === "experience") {
      // 验证所有 items 是否都有 organization 字段（ExperienceItem 必填）
      const allHaveOrganization = items.every(item => 
        item.organization !== undefined && item.organization !== null && item.organization !== ""
      );
      
      if (allHaveOrganization) {
        // 所有 items 都是有效的 ExperienceItem
        return {
          id: section.id,
          title: section.title,
          type: "experience",
          items: items
        };
      } else {
        // 存在缺少 organization 的 item，降级为 generic 类型
        // 将所有 items 转换为 GenericItem 格式
        const genericItems = items.map(item => {
          if (item.organization !== undefined) {
            // 这是一个 ExperienceItem，转换为 GenericItem
            const combinedTitle = item.organization && item.title 
              ? `${item.organization} - ${item.title}` 
              : (item.organization || item.title || "");
            const dateStr = item.date_start 
              ? (item.date_end && item.date_end !== item.date_start 
                  ? `${item.date_start} - ${item.date_end}` 
                  : item.date_start)
              : "";
            return {
              id: item.id,
              title: combinedTitle,
              date: dateStr,
              subtitle: item.location || "",
              description: Array.isArray(item.highlights) && item.highlights.length > 0
                ? item.highlights.join("; ")
                : ""
            };
          } else {
            // 已经是 GenericItem 格式，保持不变
            return {
              id: item.id,
              title: item.title || "",
              date: item.date || "",
              subtitle: item.subtitle || "",
              description: item.description || ""
            };
          }
        });
        
        return {
          id: section.id,
          title: section.title,
          type: "generic",
          items: genericItems
        };
      }
    } else if (section.type === "generic") {
      return {
        id: section.id,
        title: section.title,
        type: "generic",
        items: items
      };
    }
  }

  // 否则作为text section
  return {
    id: section.id,
    title: section.title,
    type: "text",
    content: content.trim()
  };
}

export function resumeToMarkdown(resume: any): string {
  const basics = resume?.basics || {};
  const sections = Array.isArray(resume?.sections) ? resume.sections : [];
  const lines: string[] = [];
  const esc = (x: any) => (x === null || x === undefined ? "" : String(x));
  const push = (s: string) => lines.push(s);
  const trimJoin = (arr: string[]) =>
    arr
      .map((x) => x.trim())
      .filter(Boolean)
      .join(" ");

  const nameLine = esc(basics.name);
  const contactLine = trimJoin([
    esc(basics.phone) ? `电话: ${esc(basics.phone)}` : "",
    esc(basics.email) ? `邮箱: ${esc(basics.email)}` : "",
    esc(basics.location) ? `地址: ${esc(basics.location)}` : ""
  ]);
  if (nameLine) push(`# ${nameLine}`);
  if (contactLine) push(contactLine);
  if (nameLine || contactLine) push("");

  for (const sec of sections) {
    const type = (sec as any)?.type;
    const title = esc((sec as any)?.title);
    if (title) push(`## ${title}`);
    if (type === "experience") {
      const items = (sec as any)?.items || [];
      for (const it of items) {
        const orgTitle = trimJoin([esc(it.organization), "-", esc(it.title)]);
        const date = trimJoin([esc(it.date_start), "-", esc(it.date_end)]);
        if (orgTitle || date) push(`**${orgTitle}** ${date ? `(${date})` : ""}`);
        if (esc(it.location)) push(`_${esc(it.location)}_`);
        const highlights = Array.isArray(it.highlights) ? it.highlights : [];
        for (const h of highlights) {
          if (h && String(h).trim()) push(`- ${String(h).trim()}`);
        }
        push("");
      }
    } else if (type === "generic") {
      const items = (sec as any)?.items || [];
      for (const it of items) {
        const header = trimJoin([esc(it.title), esc(it.date) ? `(${esc(it.date)})` : ""]);
        if (header) push(`**${header}**`);
        if (esc(it.subtitle)) push(`_${esc(it.subtitle)}_`);
        if (esc(it.description)) push(`${esc(it.description)}`);
        push("");
      }
    } else if (type === "text") {
      const content = esc((sec as any)?.content);
      if (content) push(content);
      push("");
    }
  }
  return lines.join("\n").trim();
}
