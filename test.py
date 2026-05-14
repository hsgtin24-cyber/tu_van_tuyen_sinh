import google.generativeai as genai

# Điền API Key của thầy vào đây
API_KEY = "AIzaSyA0eZtB-_mjs-RlIbM-Gv7pbBZ-AhSTJ1c"
genai.configure(api_key=API_KEY)

print("Đang kết nối với Google AI Studio...")
print("-" * 40)
print("DANH SÁCH CÁC MÔ HÌNH HỖ TRỢ CHAT (generateContent) CỦA THẦY LÀ:")

# Quét tất cả các mô hình mà tài khoản của thầy được phép dùng
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"👉 Tên chuẩn: {m.name}")
except Exception as e:
    print("Lỗi kết nối:", e)
    
print("-" * 40)