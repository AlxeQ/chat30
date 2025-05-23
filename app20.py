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

def analyze_interview(transcript, outline):
    prompt = f"""
你是一个专业的访谈分析专家，请根据以下步骤对访谈内容进行结构化分析：

一、分析要求
1. 识别访谈中与大纲对应的内容，分析覆盖程度
2. 特别注意发现大纲未涵盖但具有价值的案例、故事、数据等额外信息
3. 对需要深入的内容给出具体可操作的补问建议

二、结构化整理
请生成包含以下分析的Markdown表格：

| 内容类型 | 大纲问题/发现主题 | 详细摘要 | 覆盖程度 | 建议补问问题 |
|----------|-------------------|----------|----------|--------------|
# 表格内容应包含：
A. 大纲匹配部分：
   - 内容类型填写"大纲对应"
   - 覆盖程度标注（充分/部分/未覆盖）
   - 详细摘要需包含具体论据和关键数据
   - 建议补问要具体可操作（如未覆盖则必填）

B. 额外价值信息：
   - 内容类型填写"额外发现"
   - 覆盖程度标注"N/A"
   - 详细摘要需突出信息价值点
   - 建议补问可填写延伸挖掘方向

三、分析维度
1. 对每个大纲问题：
   - 提取3-5个关键信息点
   - 区分核心要点和补充信息
   - 标注受访者的典型话术

2. 对额外信息：
   - 识别有业务价值的案例（成功/失败经验）
   - 发现值得追踪的数据线索
   - 标注典型用户故事

四、格式要求
1. 使用严谨的Markdown表格格式
2. 保持各列文字简洁（每单元格不超过50字）
3. 重要内容使用**加粗**强调

请基于以下材料进行分析：
——————————
访谈大纲要求：
{outline}

访谈记录全文：
{transcript}
——————————
"""
    return call_deepseek_api(prompt)

def main():
    st.set_page_config(page_title="访谈结构整理工具", layout="wide")
    st.title("📋 访谈结构整理 MVP 工具")

    st.markdown("### 第一步：上传访谈文件（pdf、docx、txt）")
    interview_file = st.file_uploader("上传访谈记录文件：", type=["pdf", "docx", "txt"])

    st.markdown("### 第二步：上传访谈大纲（docx、txt）")
    outline_file = st.file_uploader("上传访谈大纲文件：", type=["docx", "txt"])

    if st.button("🚀 开始分析") and interview_file and outline_file:
        with st.spinner("⏳ 正在提取与分析内容，请稍候..."):
            transcript = extract_text(interview_file)
            outline = extract_text(outline_file)

            result_markdown = analyze_interview(transcript, outline)

        st.markdown("### ✅ 分析结果")
        # 修改这里：移除unsafe_allow_html=True参数
        st.markdown(result_markdown)

        # 导出Excel按钮
        try:
            df_list = pd.read_html(result_markdown, flavor="bs4")
            if df_list:
                df = df_list[0]
                st.download_button(
                    label="📥 下载结果为 Excel",
                    data=df.to_excel(index=False, engine='openpyxl'),
                    file_name="interview_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("⚠️ 未能识别表格数据，请检查返回的Markdown格式是否正确。")
        except Exception as e:
            st.error(f"❌ 转换结果失败：{e}")

if __name__ == "__main__":
    main()