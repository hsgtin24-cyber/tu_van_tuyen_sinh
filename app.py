from flask import Flask, render_template, request, jsonify
import pandas as pd
import google.generativeai as genai

app = Flask(__name__)

# ==========================================
# 1. CẤU HÌNH AI GEMINI & TÀI LIỆU RAG
# ==========================================
API_KEY = "AIzaSyA0eZtB-_mjs-RlIbM-Gv7pbBZ-AhSTJ1c" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Đọc tài liệu quy chế (Kỹ thuật RAG)
try:
    with open('quy_che.txt', 'r', encoding='utf-8') as file:
        TAI_LIEU_RAG = file.read()
except FileNotFoundError:
    TAI_LIEU_RAG = "Chưa có tài liệu quy chế tuyển sinh."

# ==========================================
# 2. ĐỌC DỮ LIỆU ĐIỂM CHUẨN TỪ EXCEL (CSV)
# ==========================================
try:
    df_diem_chuan = pd.read_csv('diem_chuan_2025.csv')
except Exception as e:
    print("CẢNH BÁO: Không tìm thấy file diem_chuan_2025.csv!")
    df_diem_chuan = pd.DataFrame(columns=['TenTruong', 'Nganh', 'Khoi', 'DiemChuan'])

# Hàm an toàn để chuyển điểm sang số thập phân
def parse_diem(val):
    try: return float(val)
    except: return 0.0

# ==========================================
# 3. CÁC API GIAO TIẾP VỚI GIAO DIỆN WEB
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_scores():
    data = request.json
    
    # Lấy điểm 6 môn
    toan = parse_diem(data.get('toan'))
    ly = parse_diem(data.get('ly'))
    hoa = parse_diem(data.get('hoa'))
    sinh = parse_diem(data.get('sinh'))
    van = parse_diem(data.get('van'))
    anh = parse_diem(data.get('anh'))

    # Tính điểm các tổ hợp khối
    khoi_diem = {
        'A00': toan + ly + hoa,
        'A01': toan + ly + anh,
        'B00': toan + hoa + sinh,
        'D01': toan + van + anh
    }

    # Tìm khối có điểm cao nhất
    khoi_toi_uu = max(khoi_diem, key=khoi_diem.get)
    diem_toi_uu = khoi_diem[khoi_toi_uu]

    an_toan, vua_suc, uoc_mo = [], [], []

    # Thuật toán phân loại trường dựa trên điểm chuẩn CSV
    if not df_diem_chuan.empty:
        df_phu_hop = df_diem_chuan[df_diem_chuan['Khoi'] == khoi_toi_uu]
        
        for index, row in df_phu_hop.iterrows():
            diem_truong = float(row['DiemChuan'])
            chenh_lech = diem_toi_uu - diem_truong
            
            thong_tin = {"name": f"{row['TenTruong']} - {row['Nganh']} ({row['Khoi']})", "score": diem_truong}
            
            if chenh_lech >= 1.5:
                an_toan.append(thong_tin)
            elif -1.0 <= chenh_lech < 1.5:
                vua_suc.append(thong_tin)
            elif -3.0 <= chenh_lech < -1.0:
                uoc_mo.append(thong_tin)

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
    
    # Prompt ép AI chỉ trả lời theo tài liệu RAG
    prompt_thong_minh = f"""
    Bạn là một chuyên gia tư vấn tuyển sinh đại học nhiệt tình. 
    Nhiệm vụ của bạn là trả lời câu hỏi của học sinh. 
    YÊU CẦU BẮT BUỘC: Chỉ sử dụng thông tin trong phần [TÀI LIỆU CUNG CẤP] dưới đây để trả lời. 
    Nếu câu hỏi nằm ngoài tài liệu, hãy nói: "Rất tiếc, quy chế hiện tại tôi được cung cấp không đề cập đến vấn đề này."
    
    [TÀI LIỆU CUNG CẤP]:
    {TAI_LIEU_RAG}
    
    [CÂU HỎI CỦA HỌC SINH]: {user_msg}
    """
    
    try:
        if API_KEY == "DÁN_MÃ_API_KEY_CỦA_THẦY_VÀO_ĐÂY":
            ai_reply = "⚠️ Thầy Dương cần dán API Key của Google vào file app.py nhé!"
        else:
            response = model.generate_content(prompt_thong_minh)
            
            # Kiểm tra xem AI có trả về đoạn text hợp lệ không (tránh lỗi Safety)
            if response.parts:
                ai_reply = response.text
            else:
                ai_reply = "Rất tiếc, câu hỏi của bạn đã bị bộ lọc an toàn của hệ thống từ chối."
                
    except Exception as e:
        lỗi_chi_tiết = str(e)
        print("🚨 LỖI AI CHI TIẾT:", lỗi_chi_tiết) # In ra Terminal để thầy dễ theo dõi
        
        # Bắt đúng bệnh "Hết lượt hỏi miễn phí"
        if "429" in lỗi_chi_tiết or "quota" in lỗi_chi_tiết.lower():
            ai_reply = "⏳ Hệ thống đang xử lý quá nhiều yêu cầu. Bạn vui lòng chờ khoảng 10 giây rồi gửi lại nhé!"
        else:
            ai_reply = "Hệ thống AI đang quá tải hoặc lỗi kết nối, vui lòng thử lại sau nhé."

    return jsonify({"response": ai_reply})

if __name__ == '__main__':
    app.run(debug=True)