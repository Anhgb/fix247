# SRS – Đặc tả yêu cầu phần mềm Fix 24/7

**Phiên bản:** 1.0 · **Ngày:** 22/10/2026 · **Tài liệu gốc:** PRD Fix 24/7 v1.0 · **Chuẩn tham chiếu:** IEEE 29148 (rút gọn) · **Đối tượng đọc:** nhóm CNTT (dev, tester), nhóm QTKD (nghiệm thu), giảng viên hướng dẫn

---

## 1. Giới thiệu

### 1.1 Mục đích

Tài liệu mô tả chi tiết các yêu cầu chức năng và phi chức năng của web app **Fix 24/7** (MVP), làm cơ sở để thiết kế, lập trình, kiểm thử và nghiệm thu. Mỗi yêu cầu có mã định danh để truy vết về PRD và test case.

### 1.2 Phạm vi

Hệ thống cho phép khách hàng chẩn đoán sự cố xe máy/thiết bị gia dụng bằng AI, đặt thợ theo GPS hoặc lịch hẹn, thanh toán, đánh giá và lưu hồ sơ sức khỏe số. Thợ nhận và xử lý đơn; admin vận hành. Phạm vi MVP lấy theo mục 4 của PRD (không gồm app native, AI offline, bán phụ tùng, quảng cáo, đa thành phố).

### 1.3 Định nghĩa & viết tắt

| Thuật ngữ | Nghĩa |
| --- | --- |
| KH | Khách hàng (Customer) |
| TH | Thợ (Technician) |
| AD | Quản trị (Admin) |
| FR / NFR / BR | Yêu cầu chức năng / phi chức năng / quy tắc nghiệp vụ |
| UC | Ca sử dụng (Use case) |
| GMV | Tổng giá trị đơn hoàn thành |
| PWA | Web app cài được như ứng dụng |
| Đơn khẩn cấp / Đơn hẹn lịch | Hai chế độ đặt thợ (emergency / scheduled) |

### 1.4 Tài liệu tham chiếu

Báo cáo tổng hợp FixHome – Mechanic Pocket (Nhóm 2, ĐH Phú Xuân); PRD Fix 24/7 v1.0.

### 1.5 Giả định công nghệ (cần nhóm xác nhận)

Frontend Next.js + TypeScript + Tailwind (PWA); backend **FastAPI (Python)**; PostgreSQL + PostGIS; Redis; WebSocket; object storage S3-compatible; AI qua API Gemini/GPT-4o. Nếu nhóm chọn NestJS, chỉ các chi tiết triển khai thay đổi, yêu cầu vẫn giữ nguyên.

---

## 2. Mô tả tổng quan

### 2.1 Bối cảnh hệ thống

Hệ thống gồm ba giao diện web (Khách, Thợ, Admin) dùng chung một backend REST + WebSocket, kết nối với các dịch vụ ngoài: nhà cung cấp AI, dịch vụ bản đồ, gửi SMS/OTP, web push/Zalo OA, cổng thanh toán (VietQR, MoMo/VNPay) và kho lưu trữ media.

### 2.2 Vai trò & phân quyền

| Chức năng | KH | TH | AD | Khách vãng lai |
| --- | --- | --- | --- | --- |
| Xem trang chủ, SOS guide, trang QR | ✔ | ✔ | ✔ | ✔ |
| Tạo chẩn đoán | ✔ | – | – | ✔ (2 lần/ngày; cần đăng nhập để đặt thợ) |
| Đặt/hủy đơn, thanh toán, đánh giá | ✔ | – | – | – |
| Nhận đơn, báo giá, cập nhật trạng thái | – | ✔ (đã duyệt) | – | – |
| Quản lý hồ sơ xe/thiết bị | ✔ | – | – | – |
| Duyệt thợ, bảng giá, tranh chấp, cấu hình | – | – | ✔ | – |

### 2.3 Ràng buộc & giả định

- Hoạt động tại TP. Huế; dữ liệu địa chỉ theo Việt Nam; ngôn ngữ mặc định tiếng Việt.
- Người dùng chủ yếu dùng điện thoại, mạng 4G, trình duyệt Chrome/Safari bản mới.
- Ngân sách vận hành \~4,5–5 triệu đồng/tháng ⇒ cần giới hạn lượt gọi AI/bản đồ.
- Thanh toán MVP là trực tiếp khách → thợ; nền tảng không giữ tiền.
- Kết quả AI chỉ mang tính tham khảo, không phải kết luận kỹ thuật.

---

## 3. Đặc tả ca sử dụng (Use Case)

| Mã | Tên | Tác nhân | Truy vết PRD |
| --- | --- | --- | --- |
| UC-01 | Đăng ký/đăng nhập bằng OTP | KH, TH | AUTH-1..4 |
| UC-02 | Tạo chẩn đoán AI | KH | DIAG-1..5 |
| UC-03 | Đặt thợ khẩn cấp | KH, TH | BOOK-1,3,4,5 |
| UC-04 | Đặt thợ hẹn lịch | KH, TH | BOOK-2,3 |
| UC-05 | Báo giá cuối & duyệt giá | TH, KH | BOOK-6 |
| UC-06 | Hoàn thành, thanh toán, xác nhận | KH, TH | PAY-1..4 |
| UC-07 | Đánh giá & bảo hành | KH, TH | RATE, PAY-6 |
| UC-08 | Quản lý hồ sơ sức khỏe số | KH | HEALTH-1..3 |
| UC-09 | Đăng ký & duyệt thợ | TH, AD | TECH-1,2 |
| UC-10 | Quản lý bảng giá chuẩn | AD | ADM-2 |
| UC-11 | Xử lý tranh chấp | AD, KH, TH | ADM-3 |
| UC-12 | Quét QR địa điểm | KH | QR-1,2 |

### UC-02 – Tạo chẩn đoán AI (chi tiết mẫu)

- **Tiền điều kiện:** có kết nối mạng; người dùng chấp nhận điều khoản dữ liệu.
- **Luồng chính:** (1) chọn danh mục → (2) tải ảnh/video/âm thanh và/hoặc nhập mô tả → (3) hệ thống nén và upload media → (4) backend gọi AI → (5) kiểm tra JSON theo schema → (6) khớp `fault_code` với bảng giá → (7) hiển thị top-3 nguyên nhân, độ tin cậy, mức nghiêm trọng, cảnh báo an toàn, khoảng giá, nút «Gọi thợ».
- **Luồng thay thế:** (a) độ tin cậy cao nhất <50% → hiển thị 1–3 câu hỏi làm rõ, người dùng trả lời rồi chạy lại; (b) không khớp bảng giá → hiển thị «Cần thợ khảo sát», ẩn khoảng giá.
- **Ngoại lệ:** AI timeout (>20 giây) → thử nhà cung cấp dự phòng, nếu vẫn lỗi hiển thị thông báo và cho phép đặt thợ không cần chẩn đoán; file sai định dạng/quá dung lượng → báo lỗi tại chỗ; vượt hạn mức lượt/ngày → thông báo và gợi ý đăng nhập/đặt thợ.
- **Hậu điều kiện:** bản ghi `diagnoses` được lưu kèm `ai_output`.

### UC-03 – Đặt thợ khẩn cấp

- **Tiền điều kiện:** đã đăng nhập, cấp quyền vị trí (hoặc ghim vị trí thủ công).
- **Luồng chính:** KH xác nhận vị trí + mô tả → hệ thống hiển thị phụ thu đêm (nếu có) → KH xác nhận → hệ thống tạo đơn trạng thái `SEARCHING` → truy vấn thợ online trong 3 km, xếp hạng theo BR-03 → gửi lời mời cho thợ top-1 (hạn 60 giây) → thợ nhận → đơn `ACCEPTED`; KH thấy thông tin thợ.
- **Luồng thay thế:** thợ từ chối/hết hạn → chuyển thợ kế tiếp; sau 90 giây không có ai nhận → mở rộng 5 km; sau 5 km vẫn không có → thông báo «Chưa có thợ», đề xuất đặt lịch hoặc hiển thị hotline/SOS guide.
- **Hậu điều kiện:** có bản ghi `order_events` cho mỗi chuyển trạng thái.

### UC-05 – Báo giá cuối & duyệt giá

TH khảo sát, nhập hạng mục công/linh kiện (tên, số lượng, đơn giá, ảnh) → hệ thống so sánh với khoảng giá tham khảo; nếu tổng vượt `price_max` trên 20% hiện cảnh báo cho cả hai bên → KH chấp nhận (đơn `IN_REPAIR`) hoặc từ chối (đơn `QUOTE_REJECTED`, tính phí khảo sát theo BR-07).

### UC-06 – Hoàn thành & thanh toán

TH báo «Đã sửa xong» + ảnh sau sửa → đơn `AWAITING_CONFIRM` → KH chọn phương thức (tiền mặt/VietQR/ví) và thanh toán → KH bấm xác nhận hoặc hệ thống tự xác nhận sau 24 giờ nếu không có khiếu nại → đơn `COMPLETED` → tạo bản ghi hoa hồng và log sức khỏe số.

---

## 4. Yêu cầu chức năng chi tiết

Cột «Tiêu chí chấp nhận» là điều kiện kiểm thử tối thiểu.

### 4.1 Xác thực (FR-AUTH)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-AUTH-01 | Đăng nhập bằng SĐT Việt Nam (10 số, đầu 03/05/07/08/09) + OTP 6 số | OTP hết hạn sau 5 phút; sai 5 lần khóa 15 phút; gửi lại tối đa 3 lần/giờ |
| FR-AUTH-02 | Phiên bằng JWT access (15 phút) + refresh (30 ngày) | Hết hạn thì tự refresh; đăng xuất thu hồi refresh token |
| FR-AUTH-03 | Một số điện thoại gắn một vai trò chính; thợ cũng có thể dùng giao diện khách | Chuyển vai trò không làm mất dữ liệu |
| FR-AUTH-04 | Chấp nhận điều khoản + chính sách dữ liệu lần đầu | Chưa chấp nhận thì không tạo được chẩn đoán/đơn |

### 4.2 Chẩn đoán AI (FR-DIAG)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-DIAG-01 | Giới hạn upload: ảnh ≤5 tệp, mỗi tệp ≤8 MB (nén client còn ≤1,5 MB); video ≤30 giây, ≤50 MB; âm thanh ≤20 giây, ≤10 MB | Vi phạm bị chặn kèm thông báo tiếng Việt |
| FR-DIAG-02 | Đầu ra AI bắt buộc theo schema (mục 7.2) và được validate | JSON sai schema → thử lại tối đa 2 lần rồi báo lỗi mềm |
| FR-DIAG-03 | Hiển thị độ tin cậy dạng % và nhãn Thấp/Vừa/Cao (<50 / 50–79 / ≥80) | Nhãn khớp giá trị |
| FR-DIAG-04 | Cảnh báo an toàn nổi bật ở đầu kết quả khi `safety_warnings` không rỗng | Cảnh báo hiển thị trước phần nguyên nhân |
| FR-DIAG-05 | Khoảng giá lấy từ `fault_catalog`: công + linh kiện, làm tròn 10.000đ | Không bao giờ hiển thị giá do AI tự sinh |
| FR-DIAG-06 | Gắn nhãn «Beta» cho phân tích âm thanh; luôn hiển thị câu miễn trừ trách nhiệm | Có trong mọi màn kết quả |
| FR-DIAG-07 | Hạn mức: khách đăng nhập 10 chẩn đoán/ngày; vãng lai 2 lần/ngày | Vượt hạn mức trả mã 429 |
| FR-DIAG-08 | Cache kết quả theo hash (media + mô tả) trong 24 giờ | Cùng đầu vào không gọi AI lần hai |
| FR-DIAG-09 | Sau đơn hoàn thành, thợ gắn nhãn «chẩn đoán đúng/sai/một phần» | Lưu vào `diagnoses.verified_label` |

### 4.3 Đặt thợ & điều phối (FR-BOOK)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-BOOK-01 | Truy vấn thợ trong bán kính bằng PostGIS (`ST_DWithin`) trên thợ `is_online = true`, `approval_status = approved`, vị trí cập nhật ≤2 phút | Không trả thợ offline/chưa duyệt/quá cũ |
| FR-BOOK-02 | Điều phối tuần tự: mời từng thợ 60 giây, tối đa 5 thợ ở 3 km rồi mở rộng 5 km | Log đủ mỗi lần mời |
| FR-BOOK-03 | Đơn hẹn lịch: chọn ngày giờ từ ≥2 giờ sau, trong 7 ngày tới, khung 07:00–21:00 | Ngoài khung bị từ chối |
| FR-BOOK-04 | Hiển thị phụ thu đêm (22:00–05:00) trước khi xác nhận | Có dòng phụ thu trong tóm tắt đơn |
| FR-BOOK-05 | Chặn đặt trùng: một KH tối đa 1 đơn khẩn cấp đang mở | Đặt thêm báo lỗi |
| FR-BOOK-06 | Hủy đơn theo BR-06 | Phí/hoàn đúng quy tắc |
| FR-BOOK-07 | Nhắc lịch trước 1 giờ cho cả hai bên | Push/SMS được gửi |

### 4.4 Theo dõi đơn & chat (FR-TRACK)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-TRACK-01 | Cập nhật trạng thái real-time qua WebSocket, fallback polling 5 giây | KH thấy đổi trạng thái ≤3 giây |
| FR-TRACK-02 | Vị trí thợ gửi mỗi 10–15 giây khi `ON_THE_WAY`; ngừng khi đến nơi | Không chia sẻ vị trí ngoài trạng thái này |
| FR-TRACK-03 | Chat văn bản + ảnh trong đơn; ẩn số điện thoại | Tin nhắn lưu và có dấu thời gian |
| FR-TRACK-04 | Thông báo mỗi lần đổi trạng thái | Có push hoặc SMS |

### 4.5 Thanh toán (FR-PAY)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-PAY-01 | Hóa đơn điện tử: công, linh kiện, phụ thu, hoa hồng (nội bộ), tổng | Tổng = Σ hạng mục; sai số 0đ |
| FR-PAY-02 | VietQR động theo số tiền đơn; webhook cập nhật trạng thái | Webhook idempotent theo `provider_ref` |
| FR-PAY-03 | Thanh toán tiền mặt: thợ bấm «Đã thu tiền», KH xác nhận | Hai bên đều xác nhận |
| FR-PAY-04 | Tự xác nhận hoàn thành sau 24 giờ nếu không khiếu nại | Job định kỳ chạy mỗi 10 phút |
| FR-PAY-05 | Hoa hồng = `commission_rate` × (công + linh kiện khai báo); ghi sổ công nợ thợ | Công nợ cộng dồn đúng |
| FR-PAY-06 | Bảo hành 7 ngày (xe máy)/30 ngày (gia dụng); KH gửi yêu cầu kèm ảnh | Tạo `warranty_claims`, thông báo thợ |

### 4.6 Hồ sơ sức khỏe số (FR-HEALTH)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-HEALTH-01 | CRUD tài sản (xe/thiết bị); tối đa 10 tài sản/người | Biển số/serial không trùng trong cùng người dùng |
| FR-HEALTH-02 | Khi đơn `COMPLETED`, tự tạo `maintenance_logs` từ hạng mục đơn | Log xuất hiện ≤1 phút |
| FR-HEALTH-03 | Nhắc bảo dưỡng theo luật (thời gian hoặc km người dùng nhập) | Nhắc đúng hạn ±1 ngày |

### 4.7 Thợ (FR-TECH)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-TECH-01 | Hồ sơ: họ tên, CCCD (mã hóa), ảnh chân dung, ảnh chứng chỉ/ngành nghề, chuyên môn, khu vực | Thiếu trường bắt buộc không gửi duyệt được |
| FR-TECH-02 | Trạng thái duyệt: PENDING → APPROVED / REJECTED / SUSPENDED | Chỉ APPROVED được online |
| FR-TECH-03 | Online/offline; gửi vị trí định kỳ khi online | Tự offline sau 5 phút mất tín hiệu |
| FR-TECH-04 | Ví thợ: thu nhập, hoa hồng đã trừ, công nợ phải nộp | Số liệu khớp với đơn |
| FR-TECH-05 | Tự động tạm khóa khi điểm TB <3,5 (≥10 đánh giá) hoặc ≥3 khiếu nại hợp lệ/30 ngày | Admin được báo |

### 4.8 Đánh giá (FR-RATE)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-RATE-01 | KH đánh giá 1–5 sao + nhãn + nhận xét ≤500 ký tự, chỉ khi đơn COMPLETED | Mỗi đơn một đánh giá/bên |
| FR-RATE-02 | Thợ đánh giá KH (để phát hiện bom đơn) | Điểm không hiển thị công khai |
| FR-RATE-03 | Điểm TB thợ = trung bình có trọng số thời gian (đánh giá 30 ngày gần nhất trọng số cao hơn) | Công thức cấu hình được |

### 4.9 QR địa điểm (FR-QR)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-QR-01 | Mã QR chứa URL `/qr/{code}` không đoán được (≥10 ký tự ngẫu nhiên) | Mã sai trả 404 |
| FR-QR-02 | Quét QR điền sẵn địa chỉ/điểm; ghi lượt quét | Có thống kê quét và đơn |

### 4.10 Admin (FR-ADM)

| ID | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| FR-ADM-01 | Duyệt/từ chối/khóa thợ kèm lý do | Có log hành động admin |
| FR-ADM-02 | CRUD `fault_catalog`; nhập CSV; có phiên bản và hiệu lực | Thay đổi không ảnh hưởng đơn đã tạo |
| FR-ADM-03 | Can thiệp đơn: đổi trạng thái, hủy, gán lại thợ, ghi chú | Mọi thao tác ghi `order_events` |
| FR-ADM-04 | Cấu hình: hoa hồng, phụ thu, bán kính, hạn mức AI, phí khảo sát | Có hiệu lực cho đơn mới |
| FR-ADM-05 | Dashboard: số đơn, GMV, hoa hồng, thời gian nhận đơn, độ khớp AI | Số liệu khớp truy vấn thô |

---

## 5. Quy tắc nghiệp vụ (BR)

| ID | Quy tắc |
| --- | --- |
| BR-01 | Hoa hồng mặc định 10% (cấu hình 8–12%) trên công + linh kiện của đơn COMPLETED; phụ thu đêm không tính hoa hồng |
| BR-02 | Hoa hồng linh kiện 5–8% chỉ áp dụng cho linh kiện khai báo trên nền tảng |
| BR-03 | Xếp hạng thợ để mời: điểm = 0,4 × gần (chuẩn hóa) + 0,3 × điểm đánh giá + 0,2 × tỷ lệ nhận đơn + 0,1 × khớp chuyên môn |
| BR-04 | Phụ thu đêm 22:00–05:00, 10.000–20.000đ, tính theo giờ tạo đơn |
| BR-05 | Báo giá cuối vượt `price_max` >20% phải kèm lý do bắt buộc từ thợ |
| BR-06 | Hủy trước khi thợ xuất phát: miễn phí; sau khi thợ xuất phát: phí di chuyển theo cấu hình |
| BR-07 | KH từ chối báo giá sau khảo sát: trả phí khảo sát (đề xuất 30.000–50.000đ, cấu hình) |
| BR-08 | Tự xác nhận hoàn thành sau 24 giờ nếu không có khiếu nại |
| BR-09 | Công nợ thợ phải nộp hằng tuần; công nợ >500.000đ hoặc quá hạn 7 ngày ⇒ không nhận đơn mới |
| BR-10 | Linh kiện có giá >100.000đ phải có tên và ảnh minh chứng trong báo giá |

---

## 6. Máy trạng thái của đơn

| Trạng thái | Ý nghĩa | Chuyển tới | Bên kích hoạt |
| --- | --- | --- | --- |
| `CREATED` | Đơn mới | `SEARCHING`, `SCHEDULED`, `CANCELLED` | KH/hệ thống |
| `SEARCHING` | Đang tìm thợ (khẩn cấp) | `ACCEPTED`, `NO_TECH`, `CANCELLED` | Hệ thống/TH |
| `SCHEDULED` | Đã gán thợ, chờ đến lịch | `ON_THE_WAY`, `CANCELLED` | TH/KH |
| `ACCEPTED` | Thợ đã nhận | `ON_THE_WAY`, `CANCELLED` | TH/KH |
| `ON_THE_WAY` | Thợ đang đến | `SURVEYING`, `CANCELLED` | TH |
| `SURVEYING` | Đang khảo sát | `QUOTE_PENDING` | TH |
| `QUOTE_PENDING` | Chờ KH duyệt giá | `IN_REPAIR`, `QUOTE_REJECTED` | KH |
| `QUOTE_REJECTED` | KH từ chối giá | `CLOSED` (tính phí BR-07) | Hệ thống |
| `IN_REPAIR` | Đang sửa | `AWAITING_CONFIRM` | TH |
| `AWAITING_CONFIRM` | Chờ KH xác nhận/thanh toán | `COMPLETED`, `DISPUTED` | KH/hệ thống |
| `COMPLETED` | Hoàn thành | `WARRANTY` (nếu có) | – |
| `DISPUTED` | Tranh chấp | `COMPLETED`, `REFUNDED`, `CLOSED` | AD |
| `NO_TECH` | Không có thợ | `SEARCHING` (thử lại), `CANCELLED` | KH |

Chuyển trạng thái ngoài bảng này phải bị từ chối với mã lỗi `INVALID_TRANSITION`; mọi chuyển trạng thái đều ghi `order_events`.

---

## 7. Giao diện bên ngoài

### 7.1 Giao diện người dùng

- Mobile-first 360–430 px; nút chính cao ≥48 px; thao tác được bằng một tay.
- Trang chủ có hai nút lớn: **Xe hỏng giữa đường** và **Sửa tại nhà**.
- Màn kết quả chẩn đoán: cảnh báo an toàn → top-3 nguyên nhân → khoảng giá → nút «Gọi thợ».
- Chữ tối thiểu 16 px; tương phản đạt WCAG AA.
- Danh sách màn hình theo mục 13 của PRD.

### 7.2 Schema đầu ra AI

```json
{
  "candidates": [
    { "fault_code": "MB-ENG-VALVE-01", "name": "Hở/kêu xú-páp",
      "confidence": 0.72, "severity": "medium" }
  ],
  "safety_warnings": ["Không chạy xe tiếp nếu máy kêu to"],
  "self_checks": ["Kiểm tra mức nhớt"],
  "followup_questions": [],
  "needs_technician": true
}
```

`confidence` ∈ \[0,1\]; `severity` ∈ {low, medium, high, critical}; tối đa 3 phần tử `candidates`.

### 7.3 Giao diện dịch vụ ngoài

| Dịch vụ | Mục đích | Yêu cầu |
| --- | --- | --- |
| AI (Gemini/GPT-4o) | Chẩn đoán | Timeout 20 giây; có nhà cung cấp dự phòng; không gửi SĐT/CCCD |
| Bản đồ | Geocode, hiển thị, khoảng cách | Cache địa chỉ; giới hạn lượt |
| SMS/OTP | Xác thực | Retry 1 lần; log trạng thái gửi |
| Web Push / Zalo OA | Thông báo | Người dùng được tắt từng loại |
| VietQR / MoMo / VNPay | Thanh toán | Xác thực chữ ký webhook; idempotent |
| Object storage | Media | URL ký tạm 15 phút; kiểm tra loại tệp |

### 7.4 API

Chuẩn REST/JSON, tiền tố `/api/v1`, xác thực Bearer JWT. Danh sách endpoint theo mục 14 PRD. Quy ước lỗi:

```json
{ "error": { "code": "INVALID_TRANSITION", "message": "Không thể chuyển trạng thái", "details": {} } }
```

Mã HTTP: 400 dữ liệu sai · 401 chưa đăng nhập · 403 không đủ quyền · 404 không tồn tại · 409 xung đột trạng thái · 422 sai schema · 429 vượt hạn mức · 500/502 lỗi hệ thống/dịch vụ ngoài.

Ví dụ `POST /api/v1/orders`:

```json
{
  "mode": "emergency",
  "diagnosis_id": "uuid",
  "asset_id": "uuid",
  "location": { "lat": 16.4637, "lng": 107.5909, "address": "..." },
  "note": "Xe nổ máy rồi tắt"
}
```

---

## 8. Yêu cầu dữ liệu

- Mô hình dữ liệu logic theo mục 12 PRD; khóa chính UUID; mọi bảng có `created_at`, `updated_at`; xóa mềm cho `users`, `assets`.
- **Ràng buộc:** `orders.status` thuộc danh sách mục 6; `reviews` duy nhất theo (`order_id`, `from_user`); `orders.final_quote` ≥ 0; `technician_profiles.id_number` lưu dạng mã hóa.
- **Chỉ mục:** GIST trên vị trí thợ; (`status`, `created_at`) trên `orders`; (`asset_id`, `performed_at`) trên `maintenance_logs`.
- **Lưu giữ dữ liệu:** media chẩn đoán 12 tháng; log đơn và thanh toán 5 năm; người dùng yêu cầu xóa trong 30 ngày (trừ dữ liệu giao dịch bắt buộc giữ).
- **Sao lưu:** hằng ngày, giữ 14 ngày; kiểm tra khôi phục mỗi quý.

---

## 9. Yêu cầu phi chức năng

| ID | Nhóm | Yêu cầu đo được |
| --- | --- | --- |
| NFR-01 | Hiệu năng | LCP trang chủ <3 giây trên 4G; API thường p95 <500 ms; chẩn đoán AI p90 ≤10 giây; ghép thợ p90 ≤5 giây |
| NFR-02 | Tải | Chịu 200 người dùng đồng thời, 20 đơn/phút ở MVP |
| NFR-03 | Sẵn sàng | Uptime ≥99% (đo hằng tháng); suy giảm êm khi AI/bản đồ lỗi |
| NFR-04 | Bảo mật | HTTPS/TLS 1.2+; mã hóa CCCD AES-256; kiểm soát truy cập theo vai trò ở mọi endpoint; chống OWASP Top 10 |
| NFR-05 | Chống lạm dụng | Rate limit theo IP/tài khoản; chặn spam OTP; CAPTCHA khi nghi ngờ |
| NFR-06 | Riêng tư | Xin quyền vị trí/camera/micro đúng lúc; vị trí chính xác chỉ chia sẻ với thợ đã nhận đơn; tuân thủ quy định bảo vệ dữ liệu cá nhân của Việt Nam |
| NFR-07 | Tương thích | Chrome, Safari iOS 15+, Edge, Samsung Internet bản gần nhất |
| NFR-08 | Khả dụng | Người dùng mới đặt được thợ ≤5 thao tác từ trang chủ |
| NFR-09 | PWA | Cài được; trang `/sos-guide` và trang chủ mở được khi mất mạng nhờ cache |
| NFR-10 | Quan sát | Log có cấu trúc, trace ID theo đơn; cảnh báo khi tỉ lệ lỗi AI >10% trong 5 phút |
| NFR-11 | Bảo trì | Kiểm thử đơn vị ≥60% logic nghiệp vụ; CI chạy lint + test mỗi PR |
| NFR-12 | Chi phí | Chi phí AI + bản đồ ≤40% ngân sách vận hành tháng; cảnh báo khi đạt 80% |
| NFR-13 | Địa phương hóa | Tiếng Việt; ngày dd/MM/yyyy, tiền tệ VND; múi giờ GMT+7 |

---

## 10. Kiểm thử & nghiệm thu

### 10.1 Chiến lược

Kiểm thử đơn vị (điều phối, tính hoa hồng, máy trạng thái), tích hợp (API + DB), E2E (luồng 6.1–6.3 của PRD, dùng Playwright), hiệu năng (k6), bảo mật cơ bản (OWASP ZAP) và thử nghiệm thực địa với 10 đơn thật/giả lập tại Huế.

### 10.2 Kịch bản nghiệm thu chính

| Mã | Kịch bản | Kết quả mong đợi |
| --- | --- | --- |
| AT-01 | KH tạo chẩn đoán từ ảnh + mô tả | Có top-3, độ tin cậy, khoảng giá từ bảng chuẩn, miễn trừ trách nhiệm |
| AT-02 | Đặt thợ khẩn cấp ban đêm | Hiện phụ thu; thợ gần nhất nhận; đơn đi hết trạng thái đến COMPLETED |
| AT-03 | Không có thợ trong 3 km | Mở rộng 5 km, sau đó báo NO\_TECH |
| AT-04 | Báo giá vượt 20% khoảng tham khảo | Cảnh báo hai bên; yêu cầu lý do |
| AT-05 | KH không xác nhận sau 24 giờ | Tự COMPLETED, tạo log sức khỏe |
| AT-06 | Webhook thanh toán gửi hai lần | Chỉ ghi nhận một lần |
| AT-07 | Thợ chưa duyệt cố bật online | Bị chặn |
| AT-08 | Quét QR | Trang đặt điền sẵn địa chỉ, ghi lượt quét |
| AT-09 | AI lỗi/timeout | Dùng nhà cung cấp dự phòng, hoặc cho đặt thợ không cần chẩn đoán |
| AT-10 | Chuyển trạng thái sai | Trả 409 `INVALID_TRANSITION` |

### 10.3 Ma trận truy vết rút gọn

| PRD | SRS | Kiểm thử |
| --- | --- | --- |
| DIAG | FR-DIAG, UC-02 | AT-01, AT-09 |
| BOOK | FR-BOOK, UC-03/04, BR-03/04/06 | AT-02, AT-03 |
| BOOK-6 | FR-BOOK, UC-05, BR-05/07 | AT-04 |
| PAY | FR-PAY, UC-06, BR-01/08 | AT-05, AT-06 |
| TECH | FR-TECH, UC-09 | AT-07 |
| QR | FR-QR, UC-12 | AT-08 |
| Máy trạng thái | Mục 6 | AT-10 |

---

## 11. Rủi ro kỹ thuật & giả định cần xác nhận

1. Cổng thanh toán có hỗ trợ webhook và hạn mức cho tài khoản cá nhân/hộ kinh doanh không (ảnh hưởng FR-PAY-02).
2. Chọn backend FastAPI hay NestJS (mục 1.5).
3. Nhà cung cấp bản đồ (Google vs Goong/OSM) quyết định chi phí và cách geocode.
4. Quy tắc phí hủy/khảo sát (BR-06/07) cần QTKD chốt con số cuối.
5. Bảng giá chuẩn 50–80 lỗi đầu tiên cần có trước khi mở chẩn đoán thật (phụ thuộc nhóm QTKD).
6. Âm thanh gửi trực tiếp cho model hay phiên âm trước: cần thử nghiệm độ chính xác trước khi mở rộng tính năng beta.

---

## Phụ lục – Lịch sử phiên bản

| Phiên bản | Ngày | Nội dung |
| --- | --- | --- |
| 1.0 | 22/10/2026 | Bản đầu, dựa trên PRD v1.0 |
