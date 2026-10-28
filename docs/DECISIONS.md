# DECISIONS.md – Fix 24/7: Giả định, mâu thuẫn, và quyết định thiết kế

**Người viết:** AI Tech Lead  
**Ngày:** 23/10/2026  
**Nguyên tắc:** SRS > PRD. Mọi điều mơ hồ không có trong tài liệu được ghi ở đây và có quyết định rõ ràng.

---

## 1. Xung đột giữa PRD và SRS

| # | Chủ đề | PRD | SRS | Quyết định |
|---|--------|-----|-----|-----------|
| C-01 | Backend stack | PRD mục 11 nêu "NestJS hoặc FastAPI" | SRS mục 1.5 nêu "FastAPI (Python)" làm mặc định | **FastAPI (Python 3.11+)** theo AGENTS.md (stack cố định). |
| C-02 | Thanh toán Escrow | PRD mục 9 nói MVP dùng thanh toán trực tiếp KH→TH, PAY-5 là P2 | SRS FR-PAY-02 đặc tả VietQR dynamic + webhook | **Giữ FR-PAY-02 (VietQR mock)** nhưng không thực thi giữ tiền. PAY-5 = P2, bỏ khỏi MVP. |
| C-03 | Phụ thu đêm | PRD mục 8 nói "100% trả cho thợ hoặc tách theo cấu hình" | SRS BR-01 nói "phụ thu đêm không tính hoa hồng" | **Phụ thu đêm không tính hoa hồng** (100% về thợ). Admin cấu hình sau. |
| C-04 | Số lần OTP | PRD không đặc tả giới hạn OTP | SRS FR-AUTH-01: sai 5 lần khóa 15 phút, gửi lại tối đa 3 lần/giờ | **Theo SRS FR-AUTH-01** hoàn toàn. |
| C-05 | Thời hạn bảo hành | PRD mục 8: "7 ngày (xe máy), 30 ngày (gia dụng)" | SRS FR-PAY-06: "7 ngày (xe máy)/30 ngày (gia dụng)" | **Nhất quán** – không có xung đột thực sự. |

---

## 2. Mơ hồ trong tài liệu và quyết định

| # | Mơ hồ | Quyết định |
|---|--------|-----------|
| A-01 | **Hoa hồng linh kiện (BR-02):** "linh kiện khai báo trên nền tảng" chưa định nghĩa | Hiểu là `order_items.type = 'part'` được thêm qua giao diện báo giá. Tỷ lệ mặc định 6%, cấu hình được trong admin. |
| A-02 | **Xếp hạng thợ BR-03:** "tỷ lệ nhận đơn" không nêu kỳ hạn | Tính trong 30 ngày gần nhất. |
| A-03 | **Mã QR (FR-QR-01):** "≥10 ký tự ngẫu nhiên" chưa nêu charset | Dùng `secrets.token_urlsafe(8)` → 11 ký tự base64url, đủ entropy. |
| A-04 | **Vị trí "quá cũ" (FR-BOOK-01):** "vị trí cập nhật ≤2 phút" | Lọc `technician_profiles.location_updated_at > now() - interval '2 minutes'`. |
| A-05 | **Google Maps vs Goong/OSM (PRD mục 18, câu hỏi 5):** chưa chốt | **Dev/mock:** Frontend hiển thị bản đồ qua OpenStreetMap (Leaflet.js) – không cần API key. Google Maps bật qua env sau. |
| A-06 | **Phí khảo sát/hủy (BR-06, BR-07):** chưa có con số chốt | Mặc định `survey_fee = 30000`, `travel_fee = 20000` VND trong bảng `platform_config`. Admin chỉnh được. |
| A-07 | **Định dạng số điện thoại:** chưa nói có mã vùng không | Lưu chuẩn hóa dạng `0xxxxxxxxx` (10 số). Validate regex: `^(03|05|07|08|09)[0-9]{8}$`. |
| A-08 | **Bảng giá chuẩn 50–80 lỗi:** nhóm QTKD chưa cung cấp | Seed 60+ lỗi thực tế với tên tiếng Việt và khoảng giá thị trường Huế. QTKD cần review trước go-live. |
| A-09 | **CCCD mã hóa:** SRS NFR-04 yêu cầu AES-256 – cần key quản lý | Key từ biến môi trường `ENCRYPTION_KEY`. Dev dùng key giả trong `.env.example`. |
| A-10 | **"Một số điện thoại gắn một vai trò chính" (FR-AUTH-03)** nhưng "thợ cũng có thể dùng giao diện khách" | Bảng `users` có `role` enum (customer, technician, admin). Thợ gọi được endpoint customer. Không có multi-role trong MVP. |
| A-11 | **Chứng chỉ thợ:** số lượng không giới hạn? | Tối đa 5 file, mỗi file ≤5 MB. |
| A-12 | **Service worker scope:** trang nào cache offline? | Cache `/`, `/sos-guide` và static assets. Chiến lược `Cache-First`. |
| A-13 | **Đơn hẹn lịch timezone:** không nói rõ | Tất cả tính theo `Asia/Ho_Chi_Minh` (UTC+7). |
| A-14 | **Heartbeat thợ (FR-TECH-03):** cơ chế "5 phút mất tín hiệu" | Thợ gửi heartbeat mỗi 60 giây. Backend job mỗi 2 phút; không heartbeat 5 phút → `is_online = false`. |

---

## 3. Quyết định kỹ thuật không có trong tài liệu

| # | Quyết định | Lý do |
|---|-----------|-------|
| D-01 | **Mock provider pattern:** mọi external service implement interface + mock class là mặc định. Real impl. bật qua `PROVIDER_xxx=real` trong `.env`. | AGENTS.md yêu cầu bắt buộc. |
| D-02 | **OTP mock:** in OTP ra stdout với prefix `[OTP-MOCK]`. | Không cần SMS provider để chạy dev. |
| D-03 | **UUID v7** cho primary keys. | Monotonic – tốt hơn UUID v4 cho index, vẫn là UUID theo SRS. |
| D-04 | **Redis:** (a) OTP store (TTL 5p), (b) OTP rate limit, (c) dispatch queue, (d) WebSocket pub/sub. | Đủ scope MVP. |
| D-05 | **MinIO bucket:** `fix247-media` (private) + `fix247-public` (public read). | Link private dùng presigned URL 15 phút per SRS 7.3. |
| D-06 | **Trace ID:** `X-Trace-ID` header inject mọi request, ghi vào log JSON. | NFR-10. |
| D-07 | **Đơn vị tiền:** lưu dạng `integer` (VND, không có xu). | Tránh floating-point. |
| D-08 | **Soft delete:** chỉ `users` và `assets` theo SRS mục 8. | Giữ đơn giản, đúng spec. |
| D-09 | **CI:** GitHub Actions: `ruff + mypy` (backend), `eslint + tsc` (frontend), `pytest`, `vitest` trên mỗi PR. | NFR-11. |
| D-10 | **Maps:** Leaflet.js + OpenStreetMap tiles (free, no API key). | A-05 ở trên. |
| D-11 | **Anonymous Diagnosis:** `diagnoses.user_id` và `category_id` là `nullable=True` để hỗ trợ hạn mức 2 lần/ngày cho khách vãng lai per FR-DIAG-07. Khi khách đăng nhập đặt đơn, hệ thống liên kết diagnosis_id vào đơn hàng. | FR-DIAG-07, SRS §2.2 |
| D-12 | **Sequential Dispatch:** mời thợ tuần tự qua Redis key `dispatch:{order_id}:current_tech` (TTL 60s); mở rộng 5km sau 90s; chuyển NO_TECH nếu cạn thợ. | FR-BOOK-01/02, BR-03 |
| D-13 | **Bảo mật Chat trong đơn:** che số điện thoại regex `(0[35789]\d{8}|\b\d{10,11}\b)` thành `***` trước khi lưu vào bảng `chat_messages` và broadcast qua WebSocket. | FR-TRACK-03 |
| D-14 | **Realtime Tracking & Polling Fallback:** WebSocket `/orders/{id}/stream` subscribe kênh Redis `order:{id}` và `loc:{id}`; fallback polling mỗi 5 giây qua `/orders/{id}/events`. | FR-TRACK-01/02 |
| D-15 | **Cơ sở tính hoa hồng (BR-01):** Chỉ tính trên (tiền công `labor` + phụ tùng `part`). 100% phụ thu ban đêm `night_surcharge` thuộc về thợ kỹ thuật, không tính vào hoa hồng nền tảng. | BR-01, FR-PAY-04 |
| D-16 | **Tự động nghiệm thu đơn sau 24h (BR-08, AT-05):** Async background task quét định kỳ mỗi 10 phút các đơn `AWAITING_CONFIRM` quá 24h từ thời điểm thợ báo sửa xong; tự động chuyển sang `COMPLETED`, sinh `MaintenanceLog` và ghi nhận công nợ hoa hồng. | BR-08, AT-05 |
| D-17 | **Đánh giá thợ có trọng số thời gian (FR-RATE-03, FR-TECH-05):** Đánh giá trong 30 ngày gần nhất tính trọng số 1.5x (cũ hơn 1.0x). Tự động kích hoạt đình chỉ tạm thời (`suspended`) khi điểm trung bình < 3.5 sau tối thiểu 10 lượt đánh giá. | FR-RATE-03, FR-TECH-05 |
| D-18 | **Khóa nhận đơn do nợ hoa hồng (BR-09):** Thợ bị tự động chặn nhận đơn mới (`is_blocked = true`) khi tổng nợ hoa hồng (`debt_amount`) > 500.000 VNĐ hoặc có nợ quá hạn 7 ngày chưa đối soát. Tự động mở lại khi nộp đối soát. | BR-09 |
| D-19 | **Giới hạn và tính duy nhất của tài sản (SRS §4.2, FR-HEALTH-01):** Mỗi người dùng quản lý tối đa 10 tài sản (`vehicles` hoặc `appliances`). Trường `plate_or_serial` (biển số xe hoặc số serial máy) là duy nhất trên mỗi tài khoản (`user_id`). Hỗ trợ soft-delete khi xóa. | SRS §4.2, FR-HEALTH-01 |
| D-20 | **Quy tắc tính toán sức khỏe tài sản tự động (FR-HEALTH-01, FR-HEALTH-02):** Xe máy cần thay dầu sau 90 ngày, kiểm tra tổng quát 180 ngày; điện máy bảo dưỡng định kỳ 180 ngày. Gán nhãn `good`, `due_soon` (còn <= 14 ngày), và `needs_maintenance` (quá hạn). | FR-HEALTH-01, FR-HEALTH-02 |
| D-21 | **Khử trùng lặp thông báo nhắc lịch bảo dưỡng (FR-HEALTH-02):** Background worker quét mỗi 10 phút. Nếu một tài sản đã được gửi thông báo cùng loại trong vòng 30 ngày gần nhất thì không gửi lặp lại. Gửi qua `MockPushProvider` và `MockOTPProvider` (SMS). | FR-HEALTH-02 |
| D-22 | **Cơ chế tự động ngoại tuyến thợ mất tín hiệu (FR-TECH-03, NFR-02):** Background worker chạy mỗi 60 giây kiểm tra các thợ đang `is_online = True`. Nếu `location_updated_at < now() - 5 phút`, tự động chuyển `is_online = False` để tránh gán đơn cho thợ offline. | FR-TECH-03, NFR-02 |
| D-23 | **Công thức độ chính xác chẩn đoán AI (DIAG-9 / FR-DIAG-09):** Thợ dán nhãn sau ca sửa: `correct`, `partial`, `incorrect`. Tỷ lệ chính xác tổng thể: `(correct + 0.5 * partial) / total * 100%`, phục vụ dashboard theo dõi chất lượng AI và cải tiến prompt. | FR-DIAG-09 |
| D-24 | **Phân quyền quản trị và kiểm toán bất biến (FR-ADM-01, NFR-04):** Mọi endpoint `/api/v1/admin/*` yêu cầu vai trò `admin`. Mọi hành động can thiệp (duyệt/khóa thợ, đổi trạng thái đơn, gán lại thợ, hủy đơn, hoàn tiền khiếu nại, đổi bảng giá, cấu hình hệ thống, tạo QR) bắt buộc ghi `AdminActionLog`. | FR-ADM-01, NFR-04 |
| D-25 | **Tính bất biến của bảng giá chuẩn (FR-ADM-02, FR-DIAG-05):** Cập nhật `fault_catalog` luôn tăng số phiên bản (`version = version + 1`). Đơn hàng cũ lưu các dòng báo giá và chi phí tại thời điểm tạo/báo giá, không bị thay đổi khi bảng giá chuẩn cập nhật. Hỗ trợ import CSV. | FR-ADM-02, FR-DIAG-05 |
| D-26 | **Nguyên tắc can thiệp trạng thái đơn hàng (FR-ADM-03):** Admin can thiệp trạng thái đơn hàng bắt buộc phải tuân thủ State Machine (`transition_order()`), ghi nhận `actor_id` là `admin.id` và tự động sinh bản ghi trong `order_events`. | FR-ADM-03, SRS §6 |
| D-27 | **Trọng tài khiếu nại và hoàn tiền (UC-11, ADM-3, FR-PAY-05):** Khi admin duyệt giải quyết khiếu nại với hành động `refund`, đơn hàng tự động chuyển sang trạng thái kết thúc `REFUNDED` thông qua State Machine, ghi nhận giải trình hoàn tiền vào `order_events` và đóng tranh chấp với `resolved`. | UC-11, FR-PAY-05 |
| D-28 | **Cơ chế hạ tầng điểm đặt mã QR (UC-12, FR-QR-01, FR-QR-02, AT-08, A-03):** Mỗi điểm QR sở hữu một mã ngẫu nhiên có độ dài $\ge 10$ ký tự sinh bằng `secrets.token_urlsafe(8)`. Khách hàng quét mã được dẫn trực tiếp đến `/qr/[code]` không cần cài app; tự động điền địa chỉ và cập nhật số lượt quét, số đơn và tỷ lệ chuyển đổi. | UC-12, FR-QR-01/02, AT-08 |

---

## 4. Ngoài phạm vi MVP – không implement

- AI offline / TensorFlow Lite
- Chuỗi cung ứng phụ tùng B2B
- Escrow tự động (PAY-5, P2)
- Quảng cáo
- Mở rộng ngoài Huế
- Dashboard B2B cho chủ trọ
- Export PDF hồ sơ sức khỏe (HEALTH-4, P2)
- Chat voice/video

---

*Tài liệu này cập nhật liên tục trong suốt quá trình phát triển.*
