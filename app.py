from flask import Flask, render_template, request, jsonify
import pandas as pd
import google.generativeai as genai

app = Flask(__name__)

# ==========================================
# CẤU HÌNH AI GEMINI (Mô hình siêu tốc 2.5)
# ==========================================
API_KEY = "AIzaSyA0eZtB-_mjs-RlIbM-Gv7pbBZ-AhSTJ1c" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    with open('quy_che.txt', 'r', encoding='utf-8') as file:
        TAI_LIEU_RAG = file.read()
except FileNotFoundError:
    TAI_LIEU_RAG = "Chưa có tài liệu quy chế."

# ==========================================
# ĐỌC DỮ LIỆU ĐA PHƯƠNG THỨC
# ==========================================
try:
    df_diem_chuan = pd.read_csv('diem_chuan_2025.csv')
except Exception as e:
    print("CẢNH BÁO: Không tìm thấy file diem_chuan_2025.csv!")
    df_diem_chuan = pd.DataFrame(columns=['TenTruong', 'Nganh', 'PhuongThuc', 'DieuKien', 'DiemChuan'])

def parse_diem(val):
    try: return float(val)
    except: return 0.0

# ==========================================
# API XỬ LÝ
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_scores():
    data = request.json
    
    # 1. Nhận toàn bộ "Vũ khí" của thí sinh
    toan = parse_diem(data.get('toan'))
    ly = parse_diem(data.get('ly'))
    hoa = parse_diem(data.get('hoa'))
    sinh = parse_diem(data.get('sinh'))
    van = parse_diem(data.get('van'))
    anh = parse_diem(data.get('anh'))
    
    diem_dgnl = parse_diem(data.get('dgnl'))
    diem_ielts = parse_diem(data.get('ielts'))

    # Tính khối tối ưu cho Học Bạ
    khoi_diem = {
        'A00': toan + ly + hoa,
        'A01': toan + ly + anh,
        'B00': toan + hoa + sinh,
        'D01': toan + van + anh
    }
    khoi_toi_uu = max(khoi_diem, key=khoi_diem.get)
    diem_toi_uu = khoi_diem[khoi_toi_uu]

    an_toan, vua_suc, uoc_mo = [], [], []

    # 2. Thuật toán quét đa luồng
    if not df_diem_chuan.empty:
        for index, row in df_diem_chuan.iterrows():
            phuong_thuc = row['PhuongThuc']
            diem_chuan = float(row['DiemChuan'])
            ten_hien_thi = f"{row['TenTruong']} - {row['Nganh']}"
            
            thuoc_nhom = None # Biến lưu kết quả phân loại
            loi_khuyen = ""

            # LUỒNG 1: XÉT HỌC BẠ
            if phuong_thuc == 'HocBa' and row['DieuKien'] == khoi_toi_uu:
                chenh_lech = diem_toi_uu - diem_chuan
                loi_khuyen = f"Xét Học bạ ({khoi_toi_uu})"
                if chenh_lech >= 1.5: thuoc_nhom = "an_toan"
                elif -1.0 <= chenh_lech < 1.5: thuoc_nhom = "vua_suc"
                elif -3.0 <= chenh_lech < -1.0: thuoc_nhom = "uoc_mo"

            # LUỒNG 2: XÉT ĐÁNH GIÁ NĂNG LỰC
            elif phuong_thuc == 'DGNL' and diem_dgnl > 0:
                chenh_lech = diem_dgnl - diem_chuan
                loi_khuyen = "Xét điểm ĐGNL"
                if chenh_lech >= 40: thuoc_nhom = "an_toan"
                elif -30 <= chenh_lech < 40: thuoc_nhom = "vua_suc"
                elif -100 <= chenh_lech < -30: thuoc_nhom = "uoc_mo"

            # LUỒNG 3: XÉT CHỨNG CHỈ IELTS
            elif phuong_thuc == 'IELTS' and diem_ielts > 0:
                chenh_lech = diem_ielts - diem_chuan
                loi_khuyen = "Xét quy đổi IELTS"
                if chenh_lech >= 0.5: thuoc_nhom = "an_toan"
                elif 0 <= chenh_lech < 0.5: thuoc_nhom = "vua_suc"
                elif -1.0 <= chenh_lech < 0: thuoc_nhom = "uoc_mo"

            # 3. Đóng gói kết quả nếu có cơ hội đỗ
            if thuoc_nhom:
                thong_tin = {
                    "name": ten_hien_thi,
                    "method": loi_khuyen,
                    "score_req": diem_chuan
                }
                if thuoc_nhom == "an_toan": an_toan.append(thong_tin)
                elif thuoc_nhom == "vua_suc": vua_suc.append(thong_tin)
                elif thuoc_nhom == "uoc_mo": uoc_mo.append(thong_tin)

    return jsonify({
        "khoi_toi_uu": khoi_toi_uu,
        "tong_diem": round(diem_toi_uu, 2),
        "an_toan": an_toan,
        "vua_suc": vua_suc,
        "uoc_mo": uoc_mo
    })

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    user_msg = request.json.get('message', '')
    prompt_thong_minh = f"""
    Bạn là một chuyên gia tư vấn tuyển sinh. 
    Chỉ dùng thông tin trong [TÀI LIỆU] để trả lời. Nếu không có thông tin, hãy nói "Quy chế không đề cập vấn đề này".
    [TÀI LIỆU]: {TAI_LIEU_RAG}
    [HỎI]: {user_msg}
    """
    try:
        response = model.generate_content(prompt_thong_minh)
        if response.parts: ai_reply = response.text
        else: ai_reply = "Câu hỏi bị bộ lọc an toàn từ chối."
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            ai_reply = "⏳ Hệ thống đang xử lý quá nhiều yêu cầu. Vui lòng chờ 10 giây rồi thử lại!"
        else:
            ai_reply = f"Lỗi AI: {str(e)}"
    return jsonify({"response": ai_reply})

if __name__ == '__main__':
    app.run(debug=True)