import streamlit as st
from streamlit.components.v1 import html
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from streamlit.errors import StreamlitAPIException, StreamlitSecretNotFoundError
import os
import glob
import re
import base64
from PIL import Image

# --- CÁC HÀM TIỆN ÍCH ---

@st.cache_data
def rfile(name_file):
    """Đọc nội dung từ một file và loại bỏ khoảng trắng thừa."""
    try:
        with open(name_file, "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception:
        return ""

@st.cache_data
def get_image_as_base64(file_path):
    """Đọc file ảnh và chuyển đổi sang định dạng base64 để nhúng vào HTML."""
    try:
        with open(file_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

# --- CÁC HÀM XỬ LÝ NỘI DUNG ---

def inject_content(html_content, image_path=None):
    """
    Tự động chèn ảnh đại diện (nếu có) vào đầu nội dung HTML.
    """
    image_tag = ""
    if image_path and os.path.exists(image_path):
        if image_path.lower().endswith('.png'):
            mime_type = 'image/png'
        elif image_path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = 'image/jpeg'
        else:
            mime_type = None

        if mime_type:
            base64_image = get_image_as_base64(image_path)
            if base64_image:
                image_tag = f'<img src="data:{mime_type};base64,{base64_image}" alt="Ảnh nội dung" style="display: block; width: 100%; height: auto; margin: 1em auto; border-radius: 8px;">'

    if re.search(r'<body.*?>', html_content, re.IGNORECASE):
         body_tag = re.search(r'<body.*?>', html_content, re.IGNORECASE).group(0)
         html_content = html_content.replace(body_tag, f"{body_tag}{image_tag}")
    else:
         html_content = image_tag + html_content
    
    content_style = """
    <style>
        body { max-width: 800px; margin: 0 auto !important; }
        @media (max-width: 800px) {
            body { padding-left: 0.5rem !important; padding-right: 0.5rem !important; margin: 0 !important; max-width: 100%; }
            body, p, div, li, td, th { font-size: 1rem !important; line-height: 1.6 !important; word-wrap: break-word; }
            h1 { font-size: 1.5rem !important; line-height: 1.3 !important; }
            h2 { font-size: 1.3rem !important; line-height: 1.4 !important; }
            h3 { font-size: 1.2rem !important; line-height: 1.5 !important; }
        }
    </style>
    """
    if re.search(r'</head>', html_content, re.IGNORECASE):
        head_end_tag = re.search(r'</head>', html_content, re.IGNORECASE).group(0)
        html_content = html_content.replace(head_end_tag, f"{content_style}{head_end_tag}")
    else:
        html_content = content_style + html_content
        
    return html_content

# --- CÁC HÀM LẤY DỮ LIỆU ---

@st.cache_data(ttl=600)
def get_all_products_as_dicts(folder_path="product_data"):
    # Hàm này được giữ lại để không gây lỗi cho các phần khác nếu có, nhưng chatbot sẽ ưu tiên hàm mới.
    product_index = []
    if not os.path.isdir(folder_path): return []
    file_paths = [f for f in glob.glob(os.path.join(folder_path, '*.txt')) if not os.path.basename(f) == '_link.txt']
    for file_path in file_paths:
        content = rfile(file_path)
        if not content: continue
        product_dict = {}
        for line in content.split('\n'):
            if ':' in line:
                key, value_str = line.split(':', 1)
                product_dict[key.strip().lower().replace(" ", "_")] = value_str.strip()
        product_dict['original_content'] = content
        if product_dict: product_index.append(product_dict)
    return product_index

@st.cache_data(ttl=600)
def get_all_products_with_images(folder_path="product_data"):
    """Quét các thư mục con trong 'product_data' để lấy mô tả sản phẩm."""
    products_for_prompt = []
    if not os.path.isdir(folder_path): return []
    try:
        sub_dirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
    except FileNotFoundError: return []
    for dir_name in sub_dirs:
        product_path = os.path.join(folder_path, dir_name)
        txt_files = glob.glob(os.path.join(product_path, '*.txt'))
        if txt_files:
            description = rfile(txt_files[0])
            products_for_prompt.append(f"PRODUCT_ID: {dir_name}\nDESCRIPTION: {description}\n---\n")
    return "\n".join(products_for_prompt)

@st.cache_data(ttl=600)
def get_dynamic_pages(folder_path):
    pages = []
    if not os.path.isdir(folder_path): return []
    try:
        sub_dirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
    except FileNotFoundError: return []

    for dir_name in sub_dirs:
        sub_dir_path = os.path.join(folder_path, dir_name)
        html_file, txt_file, img_file = None, None, None
        for f in os.listdir(sub_dir_path):
            if f.endswith('.html'): html_file = f
            elif f.endswith('.txt'): txt_file = f
            elif f.lower().endswith(('.jpg', '.png', '.jpeg')) and not img_file: 
                img_file = f
        
        if html_file and txt_file:
            match = re.match(r'^(\d+)', dir_name)
            order = int(match.group(1)) if match else os.path.getctime(sub_dir_path)
            title = rfile(os.path.join(sub_dir_path, txt_file))
            if title:
                page_data = {
                    'order': order,
                    'title': title,
                    'html_path': os.path.join(sub_dir_path, html_file),
                    'id': f"{folder_path.replace('/', '_')}_{dir_name}"
                }
                if img_file:
                    page_data['image_path'] = os.path.join(sub_dir_path, img_file)
                pages.append(page_data)

    pages.sort(key=lambda x: x['order'])
    return pages

# --- CÁC HÀM HIỂN THỊ GIAO DIỆN (VIEW) ---

def show_chatbot():
    """Hiển thị giao diện Chatbot và xử lý logic, hỗ trợ cả văn bản và hình ảnh."""
    google_api_key = None
    try:
        google_api_key = st.secrets.get("GOOGLE_API_KEY")
    except StreamlitSecretNotFoundError:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
    except Exception as e:
        st.error(f"Lỗi khi truy cập API key: {e}")
        return

    if not google_api_key:
        st.error("Không tìm thấy Google API Key.")
        return

    try:
        genai.configure(api_key=google_api_key)
    except Exception as e:
        st.error(f"Lỗi khi cấu hình Gemini API Key: {e}")
        return

    model_name = rfile("module_gemini.txt").strip() or "gemini-1.5-flash"
    
    base_system_prompt = rfile("system_data/01.system_trainning.txt")
    product_database_string = get_all_products_with_images()
    
    system_prompt = (
        f"{base_system_prompt}\n\n"
        "You are also a visual sales assistant. If the user uploads an image, analyze it and their question. "
        "Compare their image to the product descriptions below to find the best match. "
        "Respond conversationally. For example, if you find a match, say 'Yes, we have a similar product called [Product Name]! Would you like details?' "
        "If you don't find a match, politely inform them.\n\n"
        "--- PRODUCT DATABASE FOR VISUAL SEARCH ---\n"
        f"{product_database_string}"
    )

    model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt, safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    })

    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat(history=[])
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": rfile("system_data/02.assistant.txt") or "Em có thể giúp gì cho anh/chị ạ?"}]
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "image" in msg and msg["image"] is not None:
                st.image(msg["image"], width=150)
            st.markdown(msg["content"])

    if st.session_state.uploaded_image:
        st.image(st.session_state.uploaded_image, caption="Ảnh đã chọn. Hãy đặt câu hỏi của bạn.", width=200)

    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        prompt = st.chat_input("Nhập nội dung trao đổi ở đây !")
    with col2:
        upload_placeholder = st.empty()
        with upload_placeholder:
             uploaded_file = st.file_uploader(" ", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
             if uploaded_file:
                try:
                    image = Image.open(uploaded_file)
                    st.session_state.uploaded_image = image
                    upload_placeholder.empty()
                    st.rerun()
                except Exception:
                    st.warning("⚠️ File không hợp lệ. Vui lòng chỉ tải lên file ảnh (PNG, JPG).")
                    st.session_state.uploaded_image = None


    if prompt:
        user_message = {"role": "user", "content": prompt}
        content_to_send = [prompt]
        
        if st.session_state.uploaded_image:
            user_message["image"] = st.session_state.uploaded_image
            content_to_send.insert(0, st.session_state.uploaded_image)

        st.session_state.messages.append(user_message)
        with st.chat_message("user"):
            if "image" in user_message and user_message["image"] is not None:
                st.image(user_message["image"], width=150)
            st.markdown(prompt)
        
        st.session_state.uploaded_image = None
        
        with st.chat_message("assistant"):
            with st.spinner("Trợ lý đang suy nghĩ..."):
                try:
                    response = st.session_state.chat.send_message(content_to_send)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi với Gemini: {e}")
        st.rerun()

def show_main_page():
    st.markdown('<div class="mobile-only-section">', unsafe_allow_html=True)
    with st.expander("⚙️ Tùy chọn & Thông tin"):
        if st.button("🗑️ Xóa cuộc trò chuyện", key="clear_chat_main"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        st.markdown("Một sản phẩm của [Lê Đắc Chiến](https://ledacchien.com)")
    if st.button("📚 ĐỌC TIN MỚI", use_container_width=True):
        st.session_state.view = 'info_list'
        st.rerun()
    st.divider()
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("✨ Các bài viết nổi bật")
    featured_articles = get_dynamic_pages("03bai_viet")[:3]
    if featured_articles:
        cols = st.columns(len(featured_articles), gap="medium")
        for i, article in enumerate(featured_articles):
            if 'image_path' in article:
                with cols[i]:
                    st.image(article['image_path'], use_container_width=True)
                    if st.button(article['title'], use_container_width=True, key=article['id']):
                        st.session_state.view = article['id']
                        st.session_state.current_page_path = article['html_path']
                        if 'image_path' in article:
                            st.session_state.current_image_path = article['image_path']
                        st.rerun()
    else:
        st.info("Chưa có bài viết nổi bật nào.")

    st.divider()
    if os.path.exists("system_data/logo.png"):
        _, logo_col, _ = st.columns([1,1,1])
        with logo_col: st.image("system_data/logo.png", use_container_width=True)
    st.markdown(f"<h2 style='text-align: center;'>{rfile('system_data/00.xinchao.txt') or 'Chào mừng đến với Trợ lý AI'}</h2>", unsafe_allow_html=True)
    show_chatbot()

def show_dynamic_page(html_path, image_path, back_view_state, back_button_text):
    if st.button(f"⬅️ {back_button_text}"): 
        st.session_state.view = back_view_state
        for key in ['current_page_path', 'current_image_path']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    st.divider()
    content = rfile(html_path)
    if content:
        processed_content = inject_content(content, image_path)
        html(processed_content, height=800, scrolling=True)
    else:
        st.error(f"Lỗi: Không tìm thấy nội dung tại '{html_path}'.")

def show_info_list():
    if st.button("⬅️ Quay về Trang chủ"):
        st.session_state.view = "main"
        st.rerun()
    st.divider()
    st.markdown("<h3>📚 <b>Danh sách bài viết</b></h3>", unsafe_allow_html=True)
    
    info_pages = get_dynamic_pages("trang_thong_tin")
    if info_pages:
        for page in info_pages:
            if st.button(page['title'], key=page['id'], use_container_width=True):
                st.session_state.view = page['id']
                st.session_state.current_page_path = page['html_path']
                if 'image_path' in page:
                    st.session_state.current_image_path = page['image_path']
                st.rerun()
    else:
        st.info("Hiện chưa có bài viết nào trong mục này.")

# --- HÀM CHÍNH (MAIN) ---

def main():
    st.set_page_config(page_title="Trợ lý AI", page_icon="🤖", layout="wide")
    
    with st.sidebar:
        st.title("⚙️ Tùy chọn")
        if st.button("🗑️ Xóa cuộc trò chuyện", key="clear_chat_sidebar"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        st.divider()
        st.markdown("Một sản phẩm của [Lê Đắc Chiến](https://ledacchien.com)")
        info_pages = get_dynamic_pages("trang_thong_tin")
        if info_pages:
            st.divider()
            st.markdown("<h5>📚 DANH SÁCH BÀI VIẾT</h5>", unsafe_allow_html=True)
            for page in info_pages:
                if st.button(page['title'], key=f"sidebar_{page['id']}", use_container_width=True):
                    st.session_state.view = page['id']
                    st.session_state.current_page_path = page['html_path']
                    if 'image_path' in page:
                        st.session_state.current_image_path = page['image_path']
                    st.rerun()

    # <<< BỔ SUNG CSS ĐỂ TINH GỌN NÚT TẢI ẢNH
    st.markdown("""
    <style>
        [data-testid="stToolbar"], header, #MainMenu {visibility: hidden !important;}
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="stChatMessageContent-user"]) { justify-content: flex-end; }
        div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageContent-user"]) { flex-direction: row-reverse; }
        .st-emotion-cache-1v0mbdj > div > div > div > div > div[data-testid="stVerticalBlock"] .stImage {
            height: 150px; width: 100%; overflow: hidden; border-radius: 0.5rem;
        }
        .st-emotion-cache-1v0mbdj > div > div > div > div > div[data-testid="stVerticalBlock"] .stImage img {
            height: 100%; width: 100%; object-fit: cover;
        }
        [data-testid="stChatMessages"] { min-height: 70vh; }
        section.main > div { max-width: 100% !important; }
        div[data-testid="stHtml"], div[data-testid="stHtml"] iframe { width: 100% !important; }
        [data-testid="stChatMessageContent"] p { font-size: 1rem !important; }
        .block-container { padding: 1rem 1rem 0.5rem !important; max-width: 100% !important; }
        .mobile-only-section { display: none; }
        @media (min-width: 769px) { .mobile-only-section { display: none !important; } }
        @media (max-width: 768px) {
            [data-testid="stSidebar"] { display: none; }
            .mobile-only-section { display: block; }
            .st-emotion-cache-1v0mbdj > div > div > div > div > div[data-testid="stVerticalBlock"] .stImage { height: 100px; }
            .stButton > button { font-size: 0.8rem; padding: 0.3em 0.5em; }
            .block-container { padding: 1rem 0.5rem 0.5rem !important; }
            [data-testid="stChatMessage"] [data-testid="stAvatar"] { width: 1.5rem; height: 1.5rem; }
            h2 { font-size: 1.4rem !important; line-height: 1.3 !important; }
        }

        /* === CSS TÙY CHỈNH NÚT TẢI ẢNH === */
        [data-testid="stFileUploader"] section p, [data-testid="stFileUploader"] section small {
            display: none !important;
        }
        [data-testid="stFileUploader"] section button {
            font-size: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        [data-testid="stFileUploader"] section button::before {
            content: "Nhập ảnh";
            font-size: 1rem !important;
            display: block;
            text-align: center;
            width: 100%;
        }
        [data-testid="stFileUploader"] section {
             padding: 0.25rem 0.5rem !important;
             border: none !important;
        }
        /* ================================== */
    </style>
    """, unsafe_allow_html=True)
    
    current_view = st.session_state.get("view", "main")

    if current_view == "main":
        show_main_page()
    elif current_view == 'info_list':
        show_info_list()
    elif current_view.startswith("03bai_viet_") or current_view.startswith("trang_thong_tin_"):
        html_path = st.session_state.get("current_page_path")
        image_path = st.session_state.get("current_image_path") 
        if html_path and os.path.exists(html_path):
            back_view = "info_list" if current_view.startswith("trang_thong_tin_") else "main"
            back_text = "Quay lại Danh sách tin" if back_view == "info_list" else "Quay về Trang chủ"
            show_dynamic_page(html_path, image_path, back_view, back_text)
        else:
            st.error("Không thể tìm thấy trang được yêu cầu.")
            if st.button("⬅️ Quay về Trang chủ"):
                st.session_state.view = "main"
                st.rerun()
    else:
        st.session_state.view = "main"
        st.rerun()

if __name__ == "__main__":
    main()