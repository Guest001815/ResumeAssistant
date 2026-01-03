import base64
import json
import os
import argparse
import sys
import fitz  # PyMuPDF
import logging
from typing import Generator, Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

# 将当前目录添加到路径以便导入 schema
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from model import Resume
except ImportError:
    # 如果从根目录运行，尝试导入 backend.model
    try:
        from backend.model import Resume
    except ImportError:
        print("Error: Could not import 'model'. Please run this script from the 'backend' directory.")
        sys.exit(1)

# 配置
API_KEY = "sk-meternirjoqbdttphruzmhpzruhzpfhmaysygcbgryanqxxu"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "Qwen/Qwen3-VL-8B-Instruct"

def parse_resume_content(file_content: bytes) -> Resume:
    """
    接收 PDF 文件的二进制内容，使用 DeepSeek 多模态 API 解析并返回 Resume 对象。
    """
    # 1. 读取 PDF 并将每一页转换为 base64 图像
    pdf_images = []
    try:
        # 使用 stream 打开 PDF
        doc = fitz.open(stream=file_content, filetype="pdf")
        logger.info(f"PDF has {len(doc)} pages.")
        for page_num, page in enumerate(doc):
            # 将页面渲染为 pixmap (图像)
            # zoom_x, zoom_y 控制分辨率，2.0 表示 2 倍分辨率，清晰度更高
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            pdf_images.append(img_base64)
            logger.info(f"Processed page {page_num + 1}/{len(doc)}")
        doc.close()
    except Exception as e:
        logger.error(f"Error processing PDF content: {e}")
        raise ValueError(f"Error processing PDF content: {e}")

    if not pdf_images:
        logger.error("Error: No images extracted from PDF.")
        raise ValueError("Error: No images extracted from PDF.")

    # 2. 准备客户端
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    # 3. 准备 Schema
    # 从 Pydantic 模型获取 JSON schema
    schema_json = json.dumps(Resume.model_json_schema(), ensure_ascii=False, indent=2)

    # 4. 构造提示词
    system_prompt = "你是一个专业的简历解析助手。请将用户上传的简历（可能包含多页图片）解析为结构化的 JSON 数据。"
    user_prompt_text = f"""
请分析这份简历（包含 {len(pdf_images)} 页图片），提取关键信息并将其转换为 JSON 格式。
请严格遵守以下 JSON Schema 定义：

{schema_json}

要求：
1. 输出必须是合法的 JSON 格式。
2. 严格符合上述 Schema 结构。
3. 确保 sections 列表中的每一项都有正确的 type 字段（"experience", "generic", 或 "text"）。
4. 如果简历中包含工作经历，请尽量提取为 ExperienceSection；如果包含项目或其他列表项，提取为 GenericSection。
5. 请直接返回 JSON 内容，不要包含 Markdown 格式标记（如 ```json）。
6. 请综合所有页面的信息，不要遗漏。
"""

    # 5. 构造消息（多模态）
    # 首先添加系统提示
    messages = [{"role": "system", "content": system_prompt}]
    
    # 构造用户消息内容
    user_content = []
    
    # 添加每一页的图像
    for img_base64 in pdf_images:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}"
            }
        })
    
    # 添加文本提示
    user_content.append({
        "type": "text",
        "text": user_prompt_text
    })

    # 添加用户消息
    messages.append({
        "role": "user",
        "content": user_content
    })

    logger.info(f"Sending request to {MODEL} with {len(pdf_images)} images...")
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.0, # 低温度以获得确定的输出
            # response_format={"type": "json_object"} 
        )
        
        content = response.choices[0].message.content
        if not content:
            logger.error("Error: Received empty response from API.")
            raise ValueError("Error: Received empty response from API.")
        
        logger.info(f"Received response: {content}")
        # 解析 JSON
        try:
            # 处理可能的 markdown 代码块（如果模型忽略了指令）
            clean_content = content

            # 处理特定模型的输出标记（如 GLM-4V 可能输出 <|begin_of_box|>）
            if "<|begin_of_box|>" in clean_content:
                clean_content = clean_content.replace("<|begin_of_box|>", "").replace("<|end_of_box|>", "")

            if "```json" in clean_content:
                clean_content = clean_content.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_content:
                clean_content = clean_content.split("```")[1].strip()
            
            # 去除可能存在的首尾空白字符
            clean_content = clean_content.strip()
            
            resume_data = json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.error("Error: Failed to parse API response as JSON.")
            logger.error(f"Raw Content: {content}")
            raise ValueError(f"Error: Failed to parse API response as JSON. Raw content: {content}")

        # 使用 Pydantic 验证
        try:
            resume = Resume.model_validate(resume_data)
            return resume
        except Exception as e:
            logger.error(f"Validation Error: The extracted JSON does not match the Resume schema. Details: {e}")
            # 尝试返回部分数据或者抛出错误，这里我们选择抛出错误，但附带原始数据以便调试
            # 注意：在 API 上下文中，我们可能希望捕获这个错误并返回 422
            raise ValueError(f"Validation Error: {e}. Raw data: {json.dumps(resume_data, ensure_ascii=False)}")
            
    except Exception as e:
        logger.error(f"Error during parsing: {e}")
        raise e


def parse_resume_with_progress(file_content: bytes) -> Generator[Dict[str, Any], None, None]:
    """
    带进度回调的简历解析函数（生成器版本）。
    
    Yields:
        进度事件字典，格式如下：
        - { "stage": "reading", "message": "正在读取PDF文件..." }
        - { "stage": "converting", "current": 1, "total": 3, "message": "正在转换第1/3页..." }
        - { "stage": "analyzing", "message": "AI正在分析简历内容..." }
        - { "stage": "complete", "resume": Resume对象的dict }
        - { "stage": "error", "message": "错误信息" }
    """
    try:
        # 阶段1: 读取 PDF
        yield {"stage": "reading", "message": "正在读取PDF文件..."}
        
        pdf_images = []
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(doc)
            logger.info(f"PDF has {total_pages} pages.")
            
            # 阶段2: 转换图片
            for page_num, page in enumerate(doc):
                current_page = page_num + 1
                yield {
                    "stage": "converting",
                    "current": current_page,
                    "total": total_pages,
                    "message": f"正在转换第{current_page}/{total_pages}页..."
                }
                
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                img_data = pix.tobytes("png")
                img_base64 = base64.b64encode(img_data).decode("utf-8")
                pdf_images.append(img_base64)
                logger.info(f"Processed page {current_page}/{total_pages}")
            
            doc.close()
        except Exception as e:
            logger.error(f"Error processing PDF content: {e}")
            yield {"stage": "error", "message": f"PDF处理失败: {e}"}
            return

        if not pdf_images:
            logger.error("Error: No images extracted from PDF.")
            yield {"stage": "error", "message": "无法从PDF中提取图片"}
            return

        # 阶段3: AI 分析
        yield {"stage": "analyzing", "message": "AI正在分析简历内容，请稍候..."}
        
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        schema_json = json.dumps(Resume.model_json_schema(), ensure_ascii=False, indent=2)

        system_prompt = "你是一个专业的简历解析助手。请将用户上传的简历（可能包含多页图片）解析为结构化的 JSON 数据。"
        user_prompt_text = f"""
请分析这份简历（包含 {len(pdf_images)} 页图片），提取关键信息并将其转换为 JSON 格式。
请严格遵守以下 JSON Schema 定义：

{schema_json}

要求：
1. 输出必须是合法的 JSON 格式。
2. 严格符合上述 Schema 结构。
3. 确保 sections 列表中的每一项都有正确的 type 字段（"experience", "generic", 或 "text"）。
4. 如果简历中包含工作经历，请尽量提取为 ExperienceSection；如果包含项目或其他列表项，提取为 GenericSection。
5. 请直接返回 JSON 内容，不要包含 Markdown 格式标记（如 ```json）。
6. 请综合所有页面的信息，不要遗漏。
"""

        messages = [{"role": "system", "content": system_prompt}]
        user_content = []
        
        for img_base64 in pdf_images:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
            })
        
        user_content.append({"type": "text", "text": user_prompt_text})
        messages.append({"role": "user", "content": user_content})

        logger.info(f"Sending request to {MODEL} with {len(pdf_images)} images...")
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.0,
            )
            
            content = response.choices[0].message.content
            if not content:
                logger.error("Error: Received empty response from API.")
                yield {"stage": "error", "message": "AI返回了空响应"}
                return
            
            logger.info(f"Received response: {content}")
            
            # 解析 JSON
            clean_content = content
            if "<|begin_of_box|>" in clean_content:
                clean_content = clean_content.replace("<|begin_of_box|>", "").replace("<|end_of_box|>", "")
            if "```json" in clean_content:
                clean_content = clean_content.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_content:
                clean_content = clean_content.split("```")[1].strip()
            clean_content = clean_content.strip()
            
            resume_data = json.loads(clean_content)
            resume = Resume.model_validate(resume_data)
            
            # 阶段4: 完成
            yield {
                "stage": "complete",
                "message": "解析完成！",
                "resume": resume.model_dump()
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error: Failed to parse API response as JSON. {e}")
            yield {"stage": "error", "message": "AI返回的数据格式错误，请重试"}
        except Exception as e:
            logger.error(f"Validation Error: {e}")
            yield {"stage": "error", "message": f"数据验证失败: {e}"}
            
    except Exception as e:
        logger.exception(f"Unexpected error during parsing: {e}")
        yield {"stage": "error", "message": f"解析过程出错: {e}"}


def parse_resume(pdf_path: str):
    """
    使用 DeepSeek 多模态 API 解析简历 PDF 并输出 JSON。
    为了确保模型能读取多页 PDF，我们将每一页转换为图片发送。
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    logger.info(f"Processing file: {pdf_path}")

    try:
        with open(pdf_path, "rb") as f:
            content = f.read()
        
        resume = parse_resume_content(content)
        
        # 输出
        print("\n--- Parsed Resume JSON ---")
        # print(resume.model_dump_json(indent=2, exclude_none=True))
        print("(JSON output hidden to avoid console clutter, saving to file...)")
        
        # 保存到文件
        output_file = os.path.splitext(pdf_path)[0] + "_parsed.json"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(resume.model_dump_json(indent=2, exclude_none=True))
        print(f"\nSuccessfully saved parsed resume to: {output_file}")

    except Exception as e:
        print(f"Error during parsing: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d - %(message)s",
    )
    parser = argparse.ArgumentParser(description="使用 DeepSeek 多模态 API 将简历 PDF 解析为 JSON")
    parser.add_argument("pdf_path", help="简历 PDF 文件的路径")
    args = parser.parse_args()
    
    parse_resume(args.pdf_path)
