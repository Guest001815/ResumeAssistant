export type ExportFormat = "pdf" | "html";

type Payload = {
  iframe?: HTMLIFrameElement | null;
  html?: string;
};

type ExportHandler = (payload: Payload) => Promise<void> | void;

const handlers = new Map<ExportFormat, ExportHandler>();

// ============ PDF 分页导出相关类型和函数 ============

/**
 * 测量后的元素信息
 */
interface MeasuredElement {
  type: 'header' | 'section-title' | 'item';
  sectionIndex: number;      // section索引，header为-1
  itemIndex: number;         // item索引，section-title为-1
  height: number;            // 像素高度
  element: HTMLElement;      // DOM元素引用
  sectionTitle?: string;     // section标题（用于生成HTML）
}

/**
 * 页面规划信息
 */
interface PagePlan {
  pageIndex: number;
  elements: MeasuredElement[];
  usedHeight: number;
}

/**
 * 测量简历中所有可分页元素的高度
 * 按照渲染顺序返回：header -> section-title -> items -> section-title -> items ...
 */
function measureResumeElements(container: HTMLElement): MeasuredElement[] {
  const elements: MeasuredElement[] = [];
  
  // 1. 测量 Header
  const header = container.querySelector('.header') as HTMLElement;
  if (header) {
    elements.push({
      type: 'header',
      sectionIndex: -1,
      itemIndex: -1,
      height: header.offsetHeight,
      element: header
    });
    console.log(`测量 Header: ${header.offsetHeight}px`);
  }
  
  // 2. 测量每个 Section
  const sections = container.querySelectorAll('.section');
  sections.forEach((section, sectionIndex) => {
    const sectionEl = section as HTMLElement;
    const sectionTitle = sectionEl.querySelector('.section-title') as HTMLElement;
    const sectionTitleText = sectionTitle?.textContent || `Section ${sectionIndex}`;
    
    // 2.1 测量 section-title
    if (sectionTitle) {
      elements.push({
        type: 'section-title',
        sectionIndex,
        itemIndex: -1,
        height: sectionTitle.offsetHeight,
        element: sectionTitle,
        sectionTitle: sectionTitleText
      });
      console.log(`测量 Section[${sectionIndex}] 标题 "${sectionTitleText}": ${sectionTitle.offsetHeight}px`);
    }
    
    // 2.2 测量 items（可能是 .item 或 .compact-grid）
    const items = sectionEl.querySelectorAll(':scope > .item, :scope > .compact-grid');
    items.forEach((item, itemIndex) => {
      const itemEl = item as HTMLElement;
      elements.push({
        type: 'item',
        sectionIndex,
        itemIndex,
        height: itemEl.offsetHeight,
        element: itemEl,
        sectionTitle: sectionTitleText
      });
      console.log(`测量 Section[${sectionIndex}] Item[${itemIndex}]: ${itemEl.offsetHeight}px`);
    });
    
    // 如果没有找到 items，整个 section 作为一个元素测量（针对 compact-grid 等情况）
    if (items.length === 0) {
      // 计算除了标题之外的内容高度
      const titleHeight = sectionTitle?.offsetHeight || 0;
      const contentHeight = sectionEl.offsetHeight - titleHeight;
      if (contentHeight > 0) {
        elements.push({
          type: 'item',
          sectionIndex,
          itemIndex: 0,
          height: contentHeight,
          element: sectionEl,
          sectionTitle: sectionTitleText
        });
        console.log(`测量 Section[${sectionIndex}] 整体内容: ${contentHeight}px`);
      }
    }
  });
  
  console.log(`共测量 ${elements.length} 个元素`);
  return elements;
}

/**
 * A4 页面常量（基于 794px 宽度）
 */
const A4_HEIGHT_PX = 1122;      // A4 高度（像素）
const TOP_MARGIN_PX = 40;       // 顶部边距（像素）
const BOTTOM_MARGIN_PX = 100;   // 底部边距（像素，约 25mm）

/**
 * 贪心装箱算法：规划每页放哪些元素
 * @param elements 测量后的元素列表
 * @returns 每页的规划信息
 */
function planPages(elements: MeasuredElement[]): PagePlan[] {
  const plans: PagePlan[] = [];
  
  if (elements.length === 0) {
    console.warn("没有元素需要分页");
    return plans;
  }
  
  // 每页可用高度
  const availableHeight = A4_HEIGHT_PX - TOP_MARGIN_PX - BOTTOM_MARGIN_PX;
  console.log(`每页可用高度: ${availableHeight}px`);
  
  let currentPage: PagePlan = {
    pageIndex: 0,
    elements: [],
    usedHeight: 0
  };
  
  for (let i = 0; i < elements.length; i++) {
    const elem = elements[i];
    const nextElem = i + 1 < elements.length ? elements[i + 1] : null;
    
    // 计算添加此元素所需的高度（包括可能的间距）
    let requiredHeight = elem.height;
    
    // 如果是 section-title，检查下一个元素是否是同 section 的 item
    // 如果是，需要确保至少能放下 title + 第一个 item
    if (elem.type === 'section-title' && nextElem && nextElem.sectionIndex === elem.sectionIndex) {
      // section-title 必须和至少一个 item 在同一页
      const minRequiredHeight = elem.height + nextElem.height;
      
      if (currentPage.usedHeight + minRequiredHeight > availableHeight) {
        // 当前页放不下 title + 第一个 item，需要换页
        if (currentPage.elements.length > 0) {
          plans.push(currentPage);
          console.log(`页 ${currentPage.pageIndex + 1}: ${currentPage.elements.length} 个元素, ${currentPage.usedHeight}px`);
          currentPage = {
            pageIndex: plans.length,
            elements: [],
            usedHeight: 0
          };
        }
      }
    }
    
    // 检查当前页是否能放下此元素
    if (currentPage.usedHeight + requiredHeight > availableHeight) {
      // 当前页放不下
      
      // 特殊情况：如果是第一个元素或单个元素超过一页
      if (currentPage.elements.length === 0) {
        // 单个元素超过一页高度，强制放入并警告
        console.warn(`元素 ${elem.type}[${elem.sectionIndex}][${elem.itemIndex}] 高度 ${elem.height}px 超过页面可用高度 ${availableHeight}px，将强制放入`);
        currentPage.elements.push(elem);
        currentPage.usedHeight += requiredHeight;
        
        // 完成当前页，开始新页
        plans.push(currentPage);
        console.log(`页 ${currentPage.pageIndex + 1}: ${currentPage.elements.length} 个元素, ${currentPage.usedHeight}px (超大元素)`);
        currentPage = {
          pageIndex: plans.length,
          elements: [],
          usedHeight: 0
        };
        continue;
      }
      
      // 普通情况：完成当前页，开始新页
      plans.push(currentPage);
      console.log(`页 ${currentPage.pageIndex + 1}: ${currentPage.elements.length} 个元素, ${currentPage.usedHeight}px`);
      currentPage = {
        pageIndex: plans.length,
        elements: [],
        usedHeight: 0
      };
    }
    
    // 添加元素到当前页
    currentPage.elements.push(elem);
    currentPage.usedHeight += requiredHeight;
  }
  
  // 添加最后一页
  if (currentPage.elements.length > 0) {
    plans.push(currentPage);
    console.log(`页 ${currentPage.pageIndex + 1}: ${currentPage.elements.length} 个元素, ${currentPage.usedHeight}px`);
  }
  
  console.log(`分页规划完成，共 ${plans.length} 页`);
  return plans;
}

/**
 * 简历样式（与 renderResume.ts 保持一致）
 */
const RESUME_STYLES = `
  body { margin: 0; padding: 0; font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #fff; }
  .resume-container { width: 100%; box-sizing: border-box; padding: 40px; }
  .header { text-align: center; border-bottom: 2px solid #0066cc; padding-bottom: 20px; margin-bottom: 30px; }
  .name { font-size: 28px; font-weight: bold; color: #0066cc; margin-bottom: 10px; }
  .contact-info { font-size: 13px; color: #666; margin-bottom: 5px; }
  .section { margin-bottom: 25px; }
  .section-title { font-size: 16px; font-weight: bold; color: #0066cc; border-left: 4px solid #0066cc; padding-left: 12px; margin-bottom: 15px; }
  .item { margin-bottom: 15px; }
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
  .compact-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px 16px; margin-left: 10px; }
  .compact-item { display: flex; align-items: baseline; gap: 6px; font-size: 13px; line-height: 1.6; }
  .compact-bullet { color: #0066cc; font-weight: bold; flex-shrink: 0; }
  .compact-title { color: #333; font-weight: 500; }
  .compact-subtitle { color: #666; font-size: 12px; margin-left: 4px; }
  .compact-subtitle::before { content: "("; }
  .compact-subtitle::after { content: ")"; }
`;

/**
 * 根据 PagePlan 生成单页 HTML
 * 通过克隆原始 DOM 元素来保持样式一致性
 * @param plan 页面规划
 * @returns 完整的 HTML 字符串
 */
function generatePageHtml(plan: PagePlan): string {
  const bodyParts: string[] = [];
  
  // 按 sectionIndex 分组处理元素
  let currentSectionIndex = -1;
  let currentSectionHtml: string[] = [];
  let currentSectionTitle = '';
  
  for (const elem of plan.elements) {
    if (elem.type === 'header') {
      // Header 直接克隆
      bodyParts.push(elem.element.outerHTML);
      continue;
    }
    
    // 检查是否需要开始新的 section
    if (elem.sectionIndex !== currentSectionIndex) {
      // 先完成上一个 section
      if (currentSectionHtml.length > 0) {
        bodyParts.push(`
          <div class="section">
            ${currentSectionTitle ? `<div class="section-title">${escapeHtml(currentSectionTitle)}</div>` : ''}
            ${currentSectionHtml.join('')}
          </div>
        `);
      }
      
      // 开始新的 section
      currentSectionIndex = elem.sectionIndex;
      currentSectionHtml = [];
      currentSectionTitle = '';
    }
    
    if (elem.type === 'section-title') {
      currentSectionTitle = elem.sectionTitle || '';
    } else if (elem.type === 'item') {
      // 克隆 item 元素的 HTML
      currentSectionHtml.push(elem.element.outerHTML);
    }
  }
  
  // 完成最后一个 section
  if (currentSectionHtml.length > 0 || currentSectionTitle) {
    bodyParts.push(`
      <div class="section">
        ${currentSectionTitle ? `<div class="section-title">${escapeHtml(currentSectionTitle)}</div>` : ''}
        ${currentSectionHtml.join('')}
      </div>
    `);
  }
  
  // 生成完整的 HTML 文档
  const html = `
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>个人简历 - 第 ${plan.pageIndex + 1} 页</title>
      <style>${RESUME_STYLES}</style>
    </head>
    <body>
      <div class="resume-container">
        ${bodyParts.join('')}
      </div>
    </body>
    </html>
  `;
  
  console.log(`生成第 ${plan.pageIndex + 1} 页 HTML，包含 ${plan.elements.length} 个元素`);
  return html;
}

/**
 * HTML 转义函数
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * 渲染单页 HTML 到 Canvas
 */
async function renderPageToCanvas(pageHtml: string): Promise<HTMLCanvasElement> {
  // 创建临时 iframe
  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.left = "0";
  iframe.style.top = "0";
  iframe.style.width = "794px";
  iframe.style.height = `${A4_HEIGHT_PX}px`;
  iframe.style.border = "none";
  iframe.style.zIndex = "-9999";
  iframe.style.opacity = "0";
  iframe.style.pointerEvents = "none";
  
  document.body.appendChild(iframe);
  
  try {
    // 等待 iframe 加载
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("页面渲染超时")), 10000);
      iframe.onload = () => {
        clearTimeout(timeout);
        resolve();
      };
      iframe.onerror = () => {
        clearTimeout(timeout);
        reject(new Error("页面渲染失败"));
      };
      iframe.srcdoc = pageHtml;
    });
    
    // 等待资源加载
    if (iframe.contentDocument) {
      await waitForResources(iframe.contentDocument);
    }
    
    // 短暂延迟确保 DOM 完全就绪
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // 获取 resume-container
    const container = iframe.contentDocument?.querySelector('.resume-container') as HTMLElement;
    if (!container) {
      throw new Error("无法找到 .resume-container");
    }
    
    // 使用 html2canvas 渲染
    const html2canvas = (await import("html2canvas")).default;
    const canvas = await html2canvas(container, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: "#ffffff",
      logging: false,
      scrollX: 0,
      scrollY: 0,
      width: 794,
      height: A4_HEIGHT_PX
    });
    
    return canvas;
  } finally {
    // 清理 iframe
    if (iframe.parentElement) {
      document.body.removeChild(iframe);
    }
  }
}

/**
 * 创建隐藏的 iframe 并加载完整的 HTML 文档
 * 这样可以确保 <style> 标签和完整的文档结构都被正确加载
 */
async function createHiddenIframe(html: string): Promise<HTMLIFrameElement> {
  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.left = "0"; // 放在视口内
  iframe.style.top = "0";
  iframe.style.width = "794px";
  iframe.style.height = "1122px"; // A4 比例
  iframe.style.border = "none";
  iframe.style.zIndex = "-9999"; // 置于最底层
  iframe.style.opacity = "0"; // 视觉上隐藏但仍可被html2canvas渲染
  iframe.style.pointerEvents = "none"; // 不响应鼠标事件
  
  document.body.appendChild(iframe);
  
  // 等待 iframe 加载完成
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error("iframe 加载超时"));
    }, 10000); // 10秒超时
    
    iframe.onload = () => {
      clearTimeout(timeout);
      resolve();
    };
    
    iframe.onerror = () => {
      clearTimeout(timeout);
      reject(new Error("iframe 加载失败"));
    };
    
    // 使用 srcdoc 加载完整的 HTML 文档
    iframe.srcdoc = html;
  });
  
  return iframe;
}

/**
 * 等待文档中的所有资源（字体和图片）加载完成
 */
async function waitForResources(doc: Document): Promise<void> {
  // 等待字体加载
  const fontsReady = (doc as any).fonts?.ready;
  if (fontsReady && typeof fontsReady.then === "function") {
    try {
      await fontsReady;
    } catch (e) {
      console.warn("字体加载失败，继续导出:", e);
    }
  }
  
  // 等待所有图片加载
  const imgs = Array.from(doc.querySelectorAll("img"));
  if (imgs.length > 0) {
    const imagePromises = imgs.map((img) => {
      if (img.complete) {
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          console.warn("图片加载超时:", img.src);
          resolve();
        }, 5000);
        
        const done = () => {
          clearTimeout(timeout);
          resolve();
        };
        
        img.onload = done;
        img.onerror = done;
      });
    });
    
    await Promise.all(imagePromises);
  }
}

handlers.set("html", async (payload: Payload) => {
  const { iframe, html } = payload;
  let text = html;
  try {
    if (!text && iframe && iframe.contentDocument) {
      const doc = iframe.contentDocument;
      const el = doc.documentElement;
      text = el ? el.outerHTML : doc.body?.outerHTML || "";
    }
  } catch {}
  if (!text) return;
  const blob = new Blob([text], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "resume.html";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

handlers.set("pdf", async (payload: Payload) => {
  const { iframe, html } = payload;
  let measureIframe: HTMLIFrameElement | null = null;
  
  try {
    console.log("开始导出 PDF（逐页分 Section 渲染版本）...");
    
    // ========== 阶段1：创建测量用 iframe 并获取 container ==========
    let targetElement: HTMLElement | null = null;
    
    if (html) {
      console.log("使用 html 参数创建测量 iframe");
      measureIframe = await createHiddenIframe(html);
      
      if (!measureIframe.contentDocument) {
        throw new Error("无法访问 iframe.contentDocument");
      }
      
      await waitForResources(measureIframe.contentDocument);
      targetElement = measureIframe.contentDocument.querySelector(".resume-container") as HTMLElement;
      
      if (!targetElement) {
        throw new Error("在 iframe 中找不到 .resume-container 元素");
      }
    } else if (iframe && iframe.contentDocument) {
      console.log("使用传入的 iframe 引用");
      await waitForResources(iframe.contentDocument);
      targetElement = iframe.contentDocument.querySelector(".resume-container") as HTMLElement;
      
      if (!targetElement) {
        throw new Error("在传入的 iframe 中找不到 .resume-container 元素");
      }
    }
    
    if (!targetElement) {
      throw new Error("无法获取简历内容：没有可用的 html 或 iframe");
    }
    
    // 等待 DOM 就绪
    await new Promise(resolve => setTimeout(resolve, 300));
    
    console.log("目标元素尺寸:", {
      width: targetElement.offsetWidth,
      height: targetElement.offsetHeight
    });
    
    // ========== 阶段2：测量所有元素高度 ==========
    console.log("开始测量元素高度...");
    const measuredElements = measureResumeElements(targetElement);
    
    if (measuredElements.length === 0) {
      throw new Error("没有找到可导出的内容");
    }
    
    // ========== 阶段3：贪心装箱规划分页 ==========
    console.log("开始规划分页...");
    const pagePlans = planPages(measuredElements);
    
    if (pagePlans.length === 0) {
      throw new Error("分页规划失败");
    }
    
    console.log(`规划完成，共 ${pagePlans.length} 页`);
    
    // ========== 阶段4：逐页渲染并生成 PDF ==========
    console.log("开始逐页渲染...");
    
    const { jsPDF } = await import("jspdf");
    
    const pdf = new jsPDF({
      unit: 'mm',
      format: 'a4',
      orientation: 'portrait'
    });
    
    // A4 尺寸
    const pageWidthMm = 210;
    const pageHeightMm = 297;
    
    for (let i = 0; i < pagePlans.length; i++) {
      const plan = pagePlans[i];
      
      console.log(`渲染第 ${i + 1}/${pagePlans.length} 页...`);
      
      // 生成单页 HTML
      const pageHtml = generatePageHtml(plan);
      
      // 渲染为 Canvas
      const canvas = await renderPageToCanvas(pageHtml);
      
      // 添加页面
      if (i > 0) {
        pdf.addPage();
      }
      
      // 计算图片尺寸（保持宽度，按比例计算高度）
      const imgData = canvas.toDataURL('image/jpeg', 0.95);
      const imgWidth = pageWidthMm;
      const imgHeight = (canvas.height / canvas.width) * pageWidthMm;
      
      // 添加图片到 PDF
      pdf.addImage(imgData, 'JPEG', 0, 0, imgWidth, Math.min(imgHeight, pageHeightMm));
      
      console.log(`第 ${i + 1} 页渲染完成，Canvas: ${canvas.width}x${canvas.height}px`);
    }
    
    // 保存 PDF
    pdf.save('resume.pdf');
    console.log(`PDF 导出成功！共 ${pagePlans.length} 页`);
    
  } catch (error) {
    console.error("PDF 导出失败:", error);
    
    const errorMessage = error instanceof Error ? error.message : "未知错误";
    alert(`PDF 导出失败\n\n错误详情：${errorMessage}\n\n请刷新页面后重试，或联系技术支持。`);
    
    throw error;
  } finally {
    // 清理测量用 iframe
    if (measureIframe && measureIframe.parentElement) {
      console.log("清理测量 iframe");
      document.body.removeChild(measureIframe);
    }
  }
});

export function registerExportHandler(format: ExportFormat, handler: ExportHandler) {
  handlers.set(format, handler);
}

export async function exportResume(format: ExportFormat, payload: Payload) {
  const h = handlers.get(format);
  if (!h) return;
  await h(payload);
}
