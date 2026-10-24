# PRD – Fix 24/7: Nền tảng chẩn đoán AI & kết nối thợ sửa chữa (Web App MVP)

**Phiên bản:** 1.0 · **Ngày:** 22/10/2026 · **Nguồn:** Báo cáo tổng hợp FixHome + AI-Mechanic Pocket (Nhóm 2, ĐH Phú Xuân) · **Thị trường ban đầu:** TP. Huế

---

## 1. Tóm tắt sản phẩm

**Fix 24/7** là web app (PWA, dùng tốt trên điện thoại) giúp người dùng: (1) mô tả sự cố xe máy hoặc thiết bị gia dụng bằng ảnh, video, âm thanh hoặc văn bản; (2) nhận chẩn đoán sơ bộ từ AI kèm **khoảng giá tham khảo**; (3) đặt thợ gần nhất qua GPS (cứu hộ khẩn cấp hoặc hẹn lịch tại nhà); (4) thanh toán an toàn và lưu **hồ sơ sức khỏe số** của xe/thiết bị.

**Vấn đề giải quyết:** người dùng sợ bị «vẽ bệnh», ép giá, thay linh kiện kém chất lượng và khó tìm thợ uy tín, nhất là ban đêm.

**Mục tiêu MVP (T10–T12/2026):** chứng minh được vòng lặp cốt lõi *Chẩn đoán → Báo giá tham khảo → Đặt thợ → Hoàn thành → Đánh giá* với ít nhất 30 thợ đã xác minh tại Huế và 1.000 mẫu dữ liệu sự cố.

---

## 2. Đánh giá báo cáo gốc: giữ, cải tiến, loại bỏ

PRD này không sao chép nguyên văn báo cáo mà đã lọc lại cho phù hợp với một MVP web app do nhóm sinh viên thực hiện.

### 2.1 Giữ nguyên (cốt lõi)

- Chẩn đoán AI đa mô thức bằng **API có sẵn** (Gemini/GPT-4o), không tự train model.
- Khoảng giá tham khảo minh bạch trước khi sửa.
- Kết nối thợ theo GPS (bán kính 3–5 km), cứu hộ 24/7 + đặt lịch.
- Hồ sơ sức khỏe số (Digital Health Log).
- Xếp hạng thợ minh bạch, xác minh chứng chỉ nghề.
- Mô hình hoa hồng 8–12% trên đơn hoàn thành; phụ thu đêm 10.000–20.000đ.

### 2.2 Cải tiến

| Nội dung báo cáo gốc | Cải tiến trong PRD |
| --- | --- |
| App Flutter iOS/Android + Web App | **Chỉ làm Web App (PWA)** trước: một codebase, không qua duyệt store, mở được bằng QR. Mobile native để sau MVP. |
| Hai sản phẩm FixHome và Mechanic Pocket | **Hợp nhất thành một sản phẩm** với hai «danh mục dịch vụ» (Xe máy, Gia dụng) dùng chung luồng, dữ liệu và thợ. |
| Thanh toán Escrow 24–48h | Giữ ý tưởng nhưng **triển khai theo 2 bước**: MVP dùng «xác nhận hoàn thành + đối soát thủ công/chuyển khoản cuối ngày»; giữ tiền tự động chỉ khi có đối tác cổng thanh toán hỗ trợ (xem mục 9). |
| Chẩn đoán âm thanh «chuẩn xác» | Đổi thành tính năng **thử nghiệm (beta)**, luôn hiển thị mức độ tin cậy và khuyến cáo «chỉ mang tính tham khảo». |
| Khoảng giá do AI đưa ra | Khoảng giá lấy từ **bảng giá chuẩn do admin quản lý** (theo lỗi/linh kiện/khu vực); AI chỉ chọn lỗi khớp nhất. Tránh AI «bịa giá». |
| Doanh thu >337 triệu, hòa vốn tháng 2 | Coi là **giả định kế hoạch**, cần kiểm chứng bằng KPI thực tế (mục 14), không dùng làm yêu cầu sản phẩm. |

### 2.3 Loại bỏ / hoãn khỏi MVP

| Hạng mục | Lý do |
| --- | --- |
| **AI offline (TensorFlow Lite)** | Không khả thi trên web app, tốn nguồn lực lớn; thay bằng chế độ «cứu hộ cơ bản» (hướng dẫn tĩnh lưu cache PWA + nút gọi hotline thợ gần nhất). |
| **Chuỗi cung ứng phụ tùng B2B/B2C** (thợ mua linh kiện) | Cần kho, nhà phân phối, logistics; đưa vào Giai đoạn 3 (từ T04/2027). MVP chỉ ghi nhận linh kiện đã thay vào đơn. |
| **Quảng cáo hãng dầu nhớt/điện máy** | Chưa có lưu lượng người dùng; hoãn. |
| **Tự train model/«CSDL khổng lồ»** | Thay bằng thu thập dữ liệu dần qua sử dụng thực tế (có sự đồng ý của người dùng). |
| **Mở rộng Đà Nẵng, Quảng Trị** | Ngoài phạm vi MVP. |
| **Ứng dụng B2B riêng cho chủ nhà trọ/chung cư** | MVP chỉ hỗ trợ qua QR theo địa điểm; dashboard B2B ở phiên bản sau. |

---

## 3. Đối tượng người dùng

| Persona | Mô tả | Nhu cầu chính |
| --- | --- | --- |
| **Khách hàng (Customer)** | Sinh viên, người thuê trọ, hộ gia đình, tài xế công nghệ, phượt thủ tại Huế | Biết nhanh xe/thiết bị bị gì, giá bao nhiêu, ai sửa tin cậy |
| **Thợ (Technician)** | Thợ xe máy, điện, nước, điện lạnh có chứng chỉ/kinh nghiệm | Nhận đơn gần, thu nhập minh bạch, không mất phí thuê mặt bằng |
| **Quản trị (Admin)** | Nhóm QTKD vận hành | Duyệt thợ, quản lý bảng giá, xử lý khiếu nại, xem báo cáo |
| **Chủ địa điểm (Location owner)** *(nhẹ, qua QR)* | Chủ trọ, ban quản lý | Có mã QR để cư dân gọi dịch vụ nhanh |

---

## 4. Phạm vi MVP

### 4.1 Trong phạm vi (In scope)

1. Đăng ký/đăng nhập (SĐT + OTP hoặc Google).
2. Tạo yêu cầu sửa chữa với ảnh/video/âm thanh/văn bản.
3. Chẩn đoán AI + khoảng giá tham khảo.
4. Đặt thợ: **Khẩn cấp** (xe máy, theo GPS) và **Hẹn lịch** (gia dụng).
5. Cổng thợ: đăng ký, xác minh, nhận/từ chối đơn, báo giá cuối, cập nhật trạng thái.
6. Theo dõi đơn theo thời gian thực (trạng thái + vị trí thợ ở mức cơ bản).
7. Thanh toán (tiền mặt/chuyển khoản/ví MoMo-VNPay) + xác nhận hoàn thành.
8. Đánh giá 2 chiều, bảo hành.
9. Hồ sơ sức khỏe số của xe/thiết bị.
10. Landing theo mã QR địa điểm.
11. Admin panel.

### 4.2 Ngoài phạm vi (Out of scope)

App native, AI offline, bán phụ tùng, quảng cáo, đa thành phố, chat voice/video trực tiếp, dashboard B2B riêng.

---

## 5. Yêu cầu chức năng

*Ưu tiên: **P0** = bắt buộc MVP · **P1** = nên có · **P2** = để sau.*

### 5.1 Tài khoản & hồ sơ (AUTH)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| AUTH-1 | Đăng nhập bằng SĐT + OTP; tùy chọn Google | P0 |
| AUTH-2 | Phân quyền: customer, technician, admin | P0 |
| AUTH-3 | Hồ sơ cá nhân, địa chỉ lưu sẵn (nhà, trọ) | P0 |
| AUTH-4 | Đồng ý điều khoản + chính sách dữ liệu (ảnh/âm thanh được lưu để cải thiện dịch vụ) | P0 |

### 5.2 Chẩn đoán AI (DIAG)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| DIAG-1 | Chọn danh mục: Xe máy / Điện lạnh / Điện / Nước / Thiết bị gia dụng khác | P0 |
| DIAG-2 | Tải lên tối đa 5 ảnh, 1 video ≤30 giây, 1 đoạn âm thanh ≤20 giây, và/hoặc mô tả văn bản | P0 |
| DIAG-3 | AI trả về: danh sách nguyên nhân khả dĩ (top 3) kèm **độ tin cậy %**, mức độ nghiêm trọng, việc có thể tự kiểm tra an toàn, cảnh báo an toàn (vd: rò điện, cháy xăng) | P0 |
| DIAG-4 | Khi độ tin cậy thấp (<50%), AI hỏi thêm 1–3 câu làm rõ hoặc đề nghị thợ khảo sát | P0 |
| DIAG-5 | Khoảng giá tham khảo lấy từ bảng giá chuẩn (công + linh kiện) theo lỗi đã khớp | P0 |
| DIAG-6 | Phân tích âm thanh gắn nhãn **Beta** | P1 |
| DIAG-7 | Người dùng đánh giá «chẩn đoán đúng/sai» sau khi sửa xong để thu thập dữ liệu | P1 |
| DIAG-8 | Trợ lý AI chat tư vấn thêm sau chẩn đoán | P2 |

### 5.3 Đặt thợ & điều phối (BOOK)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| BOOK-1 | **Chế độ Khẩn cấp:** lấy GPS, tìm thợ đang online trong 3 km, mở rộng tới 5 km nếu không có ai nhận sau 90 giây | P0 |
| BOOK-2 | **Chế độ Hẹn lịch:** chọn ngày giờ, địa chỉ, chọn thợ từ danh sách hoặc để hệ thống gợi ý | P0 |
| BOOK-3 | Gợi ý thợ theo: khoảng cách, điểm đánh giá, tỷ lệ nhận đơn, chuyên môn | P0 |
| BOOK-4 | Thợ có 60 giây (khẩn cấp) để nhận đơn; quá hạn tự chuyển thợ kế tiếp | P0 |
| BOOK-5 | Phụ thu khẩn cấp ban đêm 22:00–05:00 (10.000–20.000đ, admin cấu hình) hiển thị rõ trước khi xác nhận | P0 |
| BOOK-6 | Thợ khảo sát và gửi **báo giá cuối**; khách chấp nhận/từ chối. Nếu báo giá vượt khoảng giá tham khảo >20%, hệ thống cảnh báo cả hai bên | P0 |
| BOOK-7 | Hủy đơn theo quy tắc (miễn phí trước khi thợ xuất phát; có phí di chuyển sau đó) | P1 |
| BOOK-8 | Nút SOS/gọi hotline cho tình huống nguy hiểm | P1 |

### 5.4 Theo dõi đơn (TRACK)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| TRACK-1 | Trạng thái: Đã tạo → Đang tìm thợ → Thợ đã nhận → Đang di chuyển → Đang khảo sát → Chờ khách duyệt giá → Đang sửa → Chờ xác nhận → Hoàn thành / Hủy / Tranh chấp | P0 |
| TRACK-2 | Hiển thị vị trí thợ trên bản đồ (cập nhật mỗi 10–15 giây) khi đang di chuyển | P1 |
| TRACK-3 | Thông báo trạng thái qua web push / SMS / Zalo OA | P1 |
| TRACK-4 | Chat văn bản trong đơn giữa khách và thợ | P1 |

### 5.5 Thanh toán & bảo vệ khách hàng (PAY)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| PAY-1 | Phương thức: tiền mặt, chuyển khoản QR (VietQR), ví MoMo/VNPay | P0 |
| PAY-2 | Hóa đơn điện tử đơn giản: công, linh kiện (tên, giá, ảnh), phụ thu, tổng | P0 |
| PAY-3 | Khách bấm «Xác nhận hoàn thành» hoặc tự động xác nhận sau 24h nếu không có khiếu nại | P0 |
| PAY-4 | Hoa hồng nền tảng tính tự động theo mục 8; ghi sổ công nợ thợ | P0 |
| PAY-5 | Giữ tiền (escrow) tự động 24–48h với thanh toán online | P2 (cần đối tác, xem mục 9) |
| PAY-6 | Bảo hành 7–30 ngày theo loại dịch vụ; nút «Yêu cầu bảo hành» | P1 |

### 5.6 Hồ sơ sức khỏe số (HEALTH)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| HEALTH-1 | Tạo «tài sản» (xe: biển số, hãng, đời; thiết bị: loại, hãng, ngày mua, vị trí) | P0 |
| HEALTH-2 | Tự động ghi lịch sử: ngày sửa, lỗi, linh kiện thay, thợ, chi phí, ảnh | P0 |
| HEALTH-3 | Nhắc bảo dưỡng định kỳ (vd: thay nhớt mỗi 2.000 km/3 tháng, vệ sinh máy lạnh 6 tháng) qua push/SMS | P1 |
| HEALTH-4 | Xuất/chia sẻ hồ sơ dạng PDF hoặc link khi bán xe/chuyển trọ | P2 |

### 5.7 Cổng thợ (TECH)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| TECH-1 | Đăng ký: họ tên, CCCD, ảnh chân dung, chứng chỉ/ảnh nghề, khu vực hoạt động, chuyên môn | P0 |
| TECH-2 | Quy trình duyệt của admin (Chờ duyệt → Đã duyệt → Tạm khóa) | P0 |
| TECH-3 | Bật/tắt trạng thái online; chia sẻ vị trí khi online | P0 |
| TECH-4 | Nhận/từ chối đơn, xem ảnh/chẩn đoán AI của khách | P0 |
| TECH-5 | Lập báo giá, thêm linh kiện, tải ảnh trước/sau khi sửa | P0 |
| TECH-6 | Ví thợ: thu nhập, hoa hồng đã trừ, công nợ, lịch sử | P1 |
| TECH-7 | Điểm uy tín, huy hiệu; tự động khóa tạm khi điểm <3.5 hoặc nhiều khiếu nại | P1 |

### 5.8 Đánh giá (RATE)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| RATE-1 | Khách chấm 1–5 sao + nhận xét + nhãn (đúng giờ, giá đúng báo, sạch sẽ) | P0 |
| RATE-2 | Thợ đánh giá khách (để giảm bom đơn) | P1 |
| RATE-3 | Chỉ đánh giá được khi đơn đã hoàn thành (chống đánh giá ảo) | P0 |

### 5.9 QR địa điểm (QR)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| QR-1 | Admin tạo mã QR gắn với địa điểm (KTX, bãi xe, khu trọ, chung cư) | P0 |
| QR-2 | Quét QR → mở trang đặt yêu cầu với địa chỉ điền sẵn, không cần cài app | P0 |
| QR-3 | Thống kê lượt quét/đơn theo từng mã | P1 |

### 5.10 Admin (ADM)

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| ADM-1 | Duyệt/khóa thợ, xem hồ sơ | P0 |
| ADM-2 | Quản lý bảng giá chuẩn (danh mục → lỗi → công + linh kiện → khoảng giá) | P0 |
| ADM-3 | Xem/can thiệp đơn, xử lý tranh chấp, hoàn tiền | P0 |
| ADM-4 | Cấu hình hoa hồng, phụ thu, bán kính tìm thợ | P0 |
| ADM-5 | Dashboard: số đơn, GMV, doanh thu, tỷ lệ hoàn thành, thời gian nhận đơn, độ chính xác AI | P1 |
| ADM-6 | Quản lý mã QR, nội dung hướng dẫn cứu hộ cơ bản | P1 |

---

## 6. Luồng người dùng chính

### 6.1 Cứu hộ xe máy khẩn cấp

1. Khách mở web (qua QR hoặc link) → chọn **«Xe hỏng giữa đường»**.
2. Cho phép định vị → chụp ảnh/ghi âm tiếng máy/mô tả.
3. AI trả chẩn đoán sơ bộ + khoảng giá + cảnh báo an toàn (vài giây).
4. Khách bấm **«Gọi thợ gần nhất»** → hệ thống gửi đơn cho thợ trong 3 km.
5. Thợ nhận đơn → khách thấy tên, ảnh, điểm, thời gian đến dự kiến.
6. Thợ đến, khảo sát, gửi báo giá cuối → khách duyệt.
7. Sửa xong → thanh toán → khách xác nhận → đánh giá → ghi vào hồ sơ xe.

### 6.2 Hẹn thợ sửa thiết bị gia dụng

1. Khách chọn **«Sửa tại nhà»** → danh mục (tủ lạnh, máy lạnh, máy giặt, điện, nước…).
2. Tải ảnh/video/âm thanh → nhận chẩn đoán + khoảng giá.
3. Chọn ngày giờ + địa chỉ → chọn thợ gợi ý hoặc tự chọn.
4. Nhắc lịch trước 1 giờ → thợ khảo sát, báo giá, sửa.
5. Thanh toán, xác nhận, đánh giá, ghi hồ sơ thiết bị.

### 6.3 Thợ tham gia nền tảng

Đăng ký → nộp giấy tờ → admin duyệt → bật online → nhận đơn → nhận tiền (trừ hoa hồng).

---

## 7. Đặc tả mô-đun AI chẩn đoán

- **Đầu vào:** danh mục, ảnh, video (trích 3–5 khung hình), âm thanh (gửi trực tiếp tới model hỗ trợ audio hoặc chuyển phiên âm mô tả), văn bản, thông tin tài sản (hãng, đời).
- **Mô hình:** gọi API Gemini/GPT-4o (có thể cấu hình), prompt hệ thống theo từng danh mục.
- **Đầu ra bắt buộc (JSON có schema):** `candidates[{fault_code, name, confidence, severity}]`, `safety_warnings[]`, `self_checks[]`, `followup_questions[]`, `needs_technician: boolean`.
- **Ánh xạ giá:** `fault_code` khớp bảng giá chuẩn → trả `price_min`, `price_max`. Nếu không khớp → «Cần thợ khảo sát», không hiển thị giá.
- **Chính sách an toàn:** không hướng dẫn tự sửa các việc nguy hiểm (điện áp cao, gas lạnh, hệ thống xăng); luôn có câu miễn trừ «Kết quả chỉ mang tính tham khảo».
- **Chất lượng:** nhật ký mỗi lần chẩn đoán; thu nhãn đúng/sai từ thợ sau khảo sát để đo độ chính xác; mục tiêu độ khớp top-3 ≥ 70% ở cuối MVP.
- **Giới hạn chi phí:** nén ảnh phía client, giới hạn số lần chẩn đoán/ngày/người dùng, cache kết quả theo hash.

---

## 8. Quy tắc kinh doanh

| Khoản | Quy tắc |
| --- | --- |
| Hoa hồng dịch vụ sửa chữa | 8–12% giá trị đơn hoàn thành (mặc định 10%, admin chỉnh) |
| Hoa hồng linh kiện | Giai đoạn MVP: 5–8% nếu linh kiện do thợ cung cấp và khai báo trên nền tảng |
| Phụ thu khẩn cấp đêm | 10.000–20.000đ, 22:00–05:00, 100% trả cho thợ hoặc tách theo cấu hình |
| Phí khảo sát/di chuyển nếu khách từ chối sửa | Do admin cấu hình (đề xuất 30.000–50.000đ), hiển thị trước khi đặt |
| Chống thoát nền tảng | Che số điện thoại trong chat; thợ vi phạm nhiều lần bị khóa |
| Bảo hành | Mặc định 7 ngày (xe máy), 30 ngày (gia dụng); thợ chịu trách nhiệm sửa lại miễn phí |

---

## 9. Thanh toán & Escrow – hướng triển khai thực tế

Báo cáo gốc đề xuất Escrow giữ tiền 24–48h. Việc nền tảng tự giữ tiền của bên thứ ba có thể liên quan quy định về trung gian thanh toán, nên đề xuất:

1. **MVP:** khách thanh toán trực tiếp cho thợ (tiền mặt/QR). Nền tảng chỉ **xác nhận hoàn thành** và ghi nhận hoa hồng; thợ nộp hoa hồng theo công nợ hàng tuần (hoặc trừ vào lần chuyển khoản sau). Lợi ích bảo vệ khách thể hiện ở **bảo hành + xử lý tranh chấp**.
2. **Giai đoạn sau:** tích hợp cổng thanh toán (MoMo/VNPay) có hỗ trợ tách/chia và giữ tiền theo hợp đồng với đối tác được cấp phép, rồi bật PAY-5.
3. **Cần xác nhận:** tư vấn pháp lý trước khi triển khai giữ tiền.

---

## 10. Yêu cầu phi chức năng

| Nhóm | Yêu cầu |
| --- | --- |
| Hiệu năng | Trang đầu tải <3 giây trên 4G; chẩn đoán AI trả kết quả ≤10 giây (P90); ghép thợ ≤5 giây |
| Khả dụng | Uptime ≥99% giờ cao điểm; PWA cài được lên màn hình chính; trang cứu hộ cơ bản hoạt động từ cache khi mạng yếu |
| Bảo mật | HTTPS, OTP chống spam, mã hóa dữ liệu nhạy cảm (CCCD) khi lưu, phân quyền theo vai trò, link media có chữ ký/hết hạn |
| Quyền riêng tư | Xin quyền vị trí/camera/micro đúng lúc; chỉ chia sẻ vị trí chính xác với thợ đã nhận đơn; cho phép xóa dữ liệu; tuân thủ quy định bảo vệ dữ liệu cá nhân của Việt Nam |
| Tương thích | Chrome/Safari/Edge bản mới; ưu tiên màn hình 360–430px |
| Ngôn ngữ | Tiếng Việt (mặc định); chuẩn bị i18n cho tiếng Anh |
| Truy cập | Nút lớn, tương phản cao, dùng được một tay (người đang ở ngoài đường) |
| Khả năng mở rộng | Tách module để sau này thêm danh mục dịch vụ, thêm thành phố |

---

## 11. Kiến trúc kỹ thuật đề xuất

| Lớp | Đề xuất | Ghi chú |
| --- | --- | --- |
| Frontend | **Next.js (React) + TypeScript + Tailwind**, PWA (service worker, manifest) | Một codebase cho khách, thợ, admin |
| Backend | **Node.js (NestJS) hoặc Python (FastAPI)** | Nhóm có thế mạnh Python → FastAPI hợp lý |
| CSDL | **PostgreSQL + PostGIS** (truy vấn thợ theo bán kính) | Redis cho hàng đợi điều phối, cache |
| Thời gian thực | WebSocket / Server-Sent Events (hoặc Supabase Realtime) | Trạng thái đơn, vị trí thợ |
| Lưu trữ media | Object storage (S3/GCS) + CDN, link ký tạm | Nén ảnh/video phía client |
| AI | Gemini/GPT-4o qua API, lớp điều phối prompt + validate JSON | Có fallback giữa 2 nhà cung cấp |
| Bản đồ | Google Maps JS/Places API (hoặc Goong/OSM để giảm chi phí) | Cân nhắc chi phí khi lưu lượng tăng |
| Thông báo | Web Push, SMS OTP (eSMS/Twilio), Zalo OA |  |
| Thanh toán | VietQR + MoMo/VNPay | Theo mục 9 |
| Hạ tầng | Cloud (GCP/AWS) hoặc VPS + Docker; CI/CD GitHub Actions | Ngân sách vận hành \~4,5–5 triệu/tháng |

---

## 12. Mô hình dữ liệu (rút gọn)

| Bảng | Trường chính |
| --- | --- |
| `users` | id, phone, name, role, avatar, status, created\_at |
| `technician_profiles` | user\_id, id\_number (mã hóa), certificates\[\], categories\[\], service\_area, rating\_avg, rating\_count, approval\_status, is\_online, last\_lat, last\_lng |
| `assets` | id, owner\_id, type (vehicle/appliance), brand, model, year, plate\_or\_serial, location\_label |
| `service_categories` | id, name, group (motorbike/home), icon |
| `fault_catalog` | id, category\_id, fault\_code, name, labor\_min, labor\_max, parts\_min, parts\_max, safety\_notes |
| `diagnoses` | id, user\_id, asset\_id, category\_id, inputs (media refs, text), ai\_output (JSON), confidence, created\_at |
| `orders` | id, customer\_id, technician\_id, asset\_id, diagnosis\_id, mode (emergency/scheduled), address, lat, lng, scheduled\_at, status, est\_min, est\_max, final\_quote, surcharge, commission\_rate, commission\_amount, total, qr\_location\_id |
| `order_items` | id, order\_id, type (labor/part), name, qty, unit\_price, photo |
| `order_events` | id, order\_id, status, actor\_id, note, created\_at |
| `payments` | id, order\_id, method, amount, status, provider\_ref, paid\_at |
| `reviews` | id, order\_id, from\_user, to\_user, stars, tags\[\], comment |
| `warranty_claims` | id, order\_id, reason, media\[\], status |
| `maintenance_logs` | id, asset\_id, order\_id, summary, parts\[\], cost, performed\_at |
| `reminders` | id, asset\_id, rule, next\_due\_at, channel |
| `qr_locations` | id, name, type, address, lat, lng, owner\_contact, code |
| `disputes` | id, order\_id, opened\_by, reason, resolution, resolved\_by |
| `notifications` | id, user\_id, type, payload, read\_at |

---

## 13. Sơ đồ màn hình / route

**Khách hàng:** `/` (trang chủ + nút «Xe hỏng giữa đường» / «Sửa tại nhà») · `/diagnose` · `/diagnose/:id` (kết quả) · `/book/:diagnosisId` · `/orders` · `/orders/:id` (theo dõi, chat, thanh toán, đánh giá) · `/assets` · `/assets/:id` (hồ sơ sức khỏe số) · `/profile` · `/qr/:code` · `/sos-guide` (cứu hộ cơ bản dùng được offline cache).

**Thợ:** `/tech/onboarding` · `/tech/dashboard` (bật online, đơn mới) · `/tech/orders/:id` (khảo sát, báo giá, cập nhật trạng thái) · `/tech/wallet` · `/tech/profile`.

**Admin:** `/admin/technicians` · `/admin/orders` · `/admin/pricing` · `/admin/qr` · `/admin/disputes` · `/admin/settings` · `/admin/analytics`.

---

## 14. API chính (REST, rút gọn)

| Nhóm | Endpoint |
| --- | --- |
| Auth | `POST /auth/otp/request` · `POST /auth/otp/verify` · `GET /me` |
| Diagnose | `POST /diagnoses` (multipart) · `GET /diagnoses/:id` · `POST /diagnoses/:id/feedback` |
| Orders | `POST /orders` · `GET /orders` · `GET /orders/:id` · `POST /orders/:id/cancel` · `POST /orders/:id/confirm-complete` |
| Technician | `POST /tech/apply` · `PATCH /tech/status` · `POST /tech/location` · `POST /orders/:id/accept` · `POST /orders/:id/quote` · `POST /orders/:id/status` |
| Quote | `POST /orders/:id/quote/respond` (accept/reject) |
| Payments | `POST /orders/:id/pay` · `POST /payments/webhook` |
| Assets | `CRUD /assets` · `GET /assets/:id/logs` |
| Reviews | `POST /orders/:id/review` |
| Admin | `PATCH /admin/technicians/:id` · `CRUD /admin/fault-catalog` · `GET /admin/stats` · `CRUD /admin/qr` |
| Realtime | `WS /orders/:id/stream` (trạng thái, vị trí, chat) |

---

## 15. Chỉ số thành công (KPI)

| Chỉ số | Mục tiêu MVP (3 tháng đầu) | Mục tiêu 12 tháng (giả định kế hoạch) |
| --- | --- | --- |
| Thợ đã xác minh hoạt động | ≥ 30 | ≥ 100 |
| Chẩn đoán đã tạo | ≥ 1.000 | ≥ 20.000 |
| Đơn hoàn thành | ≥ 300 | ≈ 10.000 |
| Tỷ lệ chẩn đoán → đặt thợ | ≥ 15% | ≥ 20% |
| Thời gian nhận đơn khẩn cấp (trung vị) | ≤ 3 phút | ≤ 2 phút |
| Độ khớp AI top-3 (theo thợ xác nhận) | ≥ 70% | ≥ 80% |
| Điểm hài lòng | ≥ 4,3/5 | ≥ 4,5/5 |
| Tỷ lệ đơn tranh chấp | ≤ 5% | ≤ 3% |
| Doanh thu nền tảng | Theo dõi để hiệu chỉnh | ≈ 337 triệu (kế hoạch gốc) |

---

## 16. Lộ trình

| Giai đoạn | Thời gian | Nội dung |
| --- | --- | --- |
| **0 – Chuẩn bị** | 2 tuần | Chốt PRD, thiết kế UI, dựng bảng giá chuẩn 50–80 lỗi phổ biến, tuyển thợ ban đầu |
| **1 – MVP lõi** | T10–T12/2026 | AUTH, DIAG, BOOK, TRACK cơ bản, cổng thợ, admin cơ bản, thanh toán MVP, hồ sơ sức khỏe số, QR; thử nghiệm kín với 30 thợ + sinh viên |
| **2 – Ra mắt Huế** | T01–T03/2027 | Phủ QR tại KTX/bãi xe/chung cư, web push/Zalo, nhắc bảo dưỡng, ví thợ, chiến dịch TikTok «AI Bắt Bệnh – Thợ Kiểm Chứng» |
| **3 – Mở rộng** | Từ T04/2027 | Cân nhắc escrow tự động, phụ tùng B2B, dashboard chủ trọ, app native, thành phố mới |

---

## 17. Rủi ro & giải pháp

| Rủi ro | Mức | Giải pháp |
| --- | --- | --- |
| AI chẩn đoán sai gây mất niềm tin | Cao | Hiển thị độ tin cậy, luôn khuyến cáo tham khảo, giá từ bảng chuẩn, thợ xác nhận để cải thiện |
| Thiếu thợ vào giờ đêm | Cao | Ưu đãi phụ thu đêm cho thợ, tuyển nhóm «trực đêm» riêng, mở rộng bán kính tự động |
| Thợ/khách giao dịch ngoài nền tảng | Trung bình | Che số liên lạc, ưu đãi bảo hành/điểm thưởng chỉ khi đặt qua app, khóa vi phạm |
| Vấn đề pháp lý khi giữ tiền | Trung bình | Dùng thanh toán trực tiếp ở MVP, tư vấn pháp lý trước khi bật escrow |
| Chi phí API AI/bản đồ tăng | Trung bình | Nén media, giới hạn lượt, cache, cân nhắc nhà cung cấp bản đồ rẻ hơn |
| An toàn người dùng (thợ lạ vào nhà) | Cao | Xác minh CCCD, chia sẻ thông tin thợ cho khách, chia sẻ hành trình, nút SOS |
| Chất lượng dữ liệu thấp ở giai đoạn đầu | Trung bình | Chuẩn hóa form nhập, bắt buộc ảnh trước/sau từ thợ |
| Giả định tài chính chưa kiểm chứng | Trung bình | Theo dõi GMV/đơn, CAC, tỷ lệ thợ hoạt động hàng tuần; hiệu chỉnh sau 3 tháng |

---

## 18. Câu hỏi còn mở

1. Nhóm chọn **FastAPI hay NestJS** cho backend? (ảnh hưởng tốc độ phát triển)
2. Có cần **đăng ký kinh doanh/hộ kinh doanh** trước khi thu hoa hồng không?
3. Danh sách 50–80 lỗi đầu tiên và khoảng giá chuẩn sẽ do thợ đối tác hay nhóm QTKD cung cấp?
4. Chính sách hủy đơn và phí khảo sát cụ thể là bao nhiêu?
5. Dùng Google Maps hay giải pháp rẻ hơn (Goong/OSM) ở MVP?

---

## Phụ lục A – Tiêu chí nghiệm thu MVP (Definition of Done)

- [ ] Khách hoàn thành luồng Chẩn đoán → Đặt thợ → Thanh toán → Đánh giá trên điện thoại, không cần cài app.
- [ ] Thợ đăng ký, được duyệt, nhận đơn và cập nhật trạng thái tới hoàn thành.
- [ ] Admin quản lý được thợ, bảng giá, đơn và tranh chấp.
- [ ] Chẩn đoán AI trả kết quả đúng schema, kèm giá từ bảng chuẩn.
- [ ] Hồ sơ sức khỏe số tự cập nhật sau mỗi đơn hoàn thành.
- [ ] QR địa điểm mở đúng trang đặt yêu cầu với địa chỉ điền sẵn.
- [ ] Kiểm thử với ≥ 10 đơn thật/giả lập trong khu vực Huế và vượt các chỉ tiêu hiệu năng ở mục 10.

## Phụ lục B – Từ điển thuật ngữ

**GMV:** tổng giá trị đơn hoàn thành · **PWA:** web app cài được như ứng dụng · **Escrow:** giữ tiền trung gian · **Digital Health Log:** hồ sơ sức khỏe số của xe/thiết bị · **CAC:** chi phí thu hút một khách hàng.
