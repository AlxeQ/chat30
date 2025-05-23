import io
import os
import pandas as pd
import docx2txt
import tempfile
import pdfplumber
import requests
import streamlit as st

# 从环境变量读取DeepSeek API Key
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def call_deepseek_api(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"调用 DeepSeek API 失败，状态码 {response.status_code}: {response.text}"

def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_docx(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(uploaded_file.read())
        tmp.flush()
        text = docx2txt.process(tmp.name)
    return text

def extract_text(file):
    if file.name.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif file.name.endswith(".docx"):
        return extract_text_from_docx(file)
    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    else:
        return "不支持的文件类型"

def analyze_interview(transcript, outline, target):
    prompt = f"""
你是一个专业的访谈内容结构化记录专家，你的任务是帮助团队**完整还原受访者讲述的每个观点、完整案例与细节**，并将其与访谈大纲逐一比对、分类归档。

**一、大纲逐条比对**
- 请遍历以下访谈大纲中的每个问题，判断访谈中是否进行了回答。
- 若有回答，请完整提取对应内容，保留典型说法、关键数据、具体细节。
- 若无明确回答，请提出可直接用于补充访谈的具体补问建议。

**二、案例与线索抽取**
- 识别访谈中所有包含时间、人物、事件、结果的完整案例与经验分享。
- 提取其中的关键故事、成败经验、量化数据、可追问的线索。

**三、输出格式（Markdown表格）**
请生成如下格式的表格（不限于大纲问题）：

| 类型 | 问题或主题 | 内容摘要 | 原始话术 | 覆盖情况 | 补问建议 |
|------|------------|----------|-----------|-----------|-----------|
- 类型包含：大纲对应 / 案例补充 / 数据线索
- 覆盖情况请填写“是/否/部分覆盖”
- 内容摘要不少于50字，避免压缩过度
- 原始话术请节选受访者的原句
- 如有遗漏，请填写具体补问建议，问题精准可操作

---

【访谈目标】
{target}

【访谈大纲】
{outline}

【访谈原文】
{transcript}
"""
    return call_deepseek_api(prompt)

def main():
    st.set_page_config(page_title="访谈结构整理工具", layout="wide")
    st.title("📋 访谈结构整理 MVP 工具")

    # 新增访谈目标输入框
    target = st.text_area("请输入访谈目标（例如：本次访谈主要目标是什么）")

    st.markdown("### 第一步：上传访谈文件（pdf、docx、txt）")
    interview_file = st.file_uploader("上传访谈记录文件：", type=["pdf", "docx", "txt"])

    st.markdown("### 第二步：上传访谈大纲（docx、txt）")
    outline_file = st.file_uploader("上传访谈大纲文件：", type=["docx", "txt"])

    if st.button("🚀 开始分析") and interview_file and outline_file and target.strip() != "":
        with st.spinner("⏳ 正在提取与分析内容，请稍候..."):
            transcript = extract_text(interview_file)
            outline = extract_text(outline_file)
            result_markdown = analyze_interview(transcript, outline, target)

        st.markdown("### ✅ 分析结果")
        st.markdown(result_markdown)

        # 表格解析和Excel导出功能（最终修复版）
        try:
            # 检查是否是有效的markdown表格
            table_lines = [line for line in result_markdown.split('\n') 
                         if line.strip().startswith('|') and '---' not in line]
            
            if len(table_lines) >= 2:  # 至少包含表头和数据行
                # 使用更健壮的表格解析方式
                df = pd.read_csv(io.StringIO('\n'.join(table_lines)), 
                                sep='|', 
                                skipinitialspace=True,
                                header=0)
                df = df.iloc[:, 1:-1]  # 移除markdown表格首尾的空白列
                
                # 生成Excel文件（100%可靠写法）
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='分析结果')
                excel_buffer.seek(0)
                
                # 添加下载按钮
                st.download_button(
                    label="💾 下载Excel表格",
                    data=excel_buffer,
                    file_name="分析结果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.info("ℹ️ 分析结果中未包含表格数据")
                
        except pd.errors.EmptyDataError:
            st.info("ℹ️ 未检测到可转换的表格数据")
        except Exception as e:
            st.error(f"表格转换失败：{str(e)}")
