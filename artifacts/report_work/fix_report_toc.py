"""Materialize the verified page numbers in the generated report TOC."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


REPORT = Path(__file__).resolve().parents[1] / "bao-cao-tom-tat-van-ban-textrank-hutech.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PAGES = {
    "CHƯƠNG 1. TỔNG QUAN BÀI TOÁN": 7,
    "1.1. Phát biểu bài toán": 7,
    "1.2. Đầu vào, đầu ra và đơn vị xử lý": 7,
    "1.3. Mục tiêu thực hiện": 8,
    "1.4. Câu hỏi cần trả lời": 8,
    "1.5. Phạm vi và giới hạn kết luận": 8,
    "1.6. Bố cục báo cáo": 9,
    "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT": 10,
    "2.1. Tóm tắt văn bản trích xuất": 10,
    "2.2. Chuẩn hóa và tách từ": 10,
    "2.3. Term Frequency và Inverse Document Frequency": 10,
    "2.4. Chuẩn hóa L2 và cosine similarity": 11,
    "2.5. Kiểm chứng TF-IDF viết tay bằng thư viện tham chiếu": 12,
    "2.6. Đồ thị câu có trọng số": 13,
    "2.7. PageRank có trọng số": 13,
    "2.8. Lựa chọn Top-K và thứ tự nguồn": 14,
    "2.9. Định nghĩa chỉ số đánh giá": 14,
    "CHƯƠNG 3. GIẢI PHÁP VÀ QUY TRÌNH THỰC HIỆN": 16,
    "3.1. Kiến trúc tổng thể": 16,
    "3.2. Đọc dữ liệu và bảo toàn thông tin câu": 16,
    "3.3. Tạo biểu diễn câu và kiểm chứng": 17,
    "3.4. Tính độ tương đồng và dựng đồ thị": 17,
    "3.5. Tính PageRank": 17,
    "3.6. Chọn câu và tạo bản tóm tắt": 18,
    "3.7. Cấu hình thực nghiệm cuối": 18,
    "3.8. Quy trình lựa chọn tham số": 18,
    "3.9. Giả mã quy trình": 19,
    "3.10. Tính tái lập và kiểm soát sai lệch": 19,
    "3.11. Độ phức tạp": 19,
    "CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ": 20,
    "4.1. Thiết kế thực nghiệm": 20,
    "4.2. Kiểm tra TF-IDF viết tay": 20,
    "4.3. Lựa chọn K từ dữ liệu tham chiếu": 20,
    "4.4. Vai trò của ngưỡng tương đồng": 21,
    "4.5. Kết quả PageRank với Top-K = 15": 22,
    "4.6. Thực nghiệm MMR và lý do không lựa chọn": 22,
    "4.7. Kết quả cấu hình cuối trên tập huấn luyện và kiểm tra": 23,
    "4.8. Phân tích lỗi và giới hạn": 24,
    "4.9. Đối chiếu với yêu cầu bài toán": 24,
    "CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN": 26,
    "5.1. Kết quả đạt được": 26,
    "5.2. Những nội dung chưa giải quyết": 26,
    "5.3. Hướng cải tiến ưu tiên": 26,
    "5.4. Kết luận chung": 27,
    "TÀI LIỆU THAM KHẢO": 28,
}


with ZipFile(REPORT) as source:
    members = {name: source.read(name) for name in source.namelist()}

root = etree.fromstring(members["word/document.xml"])
updated = set()
for paragraph in root.xpath("//w:body/w:p", namespaces=NS):
    texts = paragraph.xpath(".//w:t", namespaces=NS)
    if len(texts) < 2:
        continue
    heading = "".join(node.text or "" for node in texts[:-1]).strip()
    if heading in PAGES and (texts[-1].text or "").strip().isdigit():
        texts[-1].text = str(PAGES[heading])
        updated.add(heading)

missing = set(PAGES) - updated
if missing:
    raise RuntimeError(f"Missing TOC entries: {sorted(missing)}")

members["word/document.xml"] = etree.tostring(
    root, xml_declaration=True, encoding="UTF-8", standalone=True
)
temporary = REPORT.with_suffix(".toc-fixed.docx")
with ZipFile(temporary, "w", ZIP_DEFLATED) as destination:
    for name, content in members.items():
        destination.writestr(name, content)
temporary.replace(REPORT)
print(f"Updated {len(updated)} TOC entries in {REPORT}")
