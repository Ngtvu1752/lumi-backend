## 4. Tài liệu Thiết kế Hệ thống (System Design Document - SDD)
Thiết kế kiến trúc này được xây dựng xung quanh nguyên lý chia tách trách nhiệm (Separation of Concerns). Mobile app đóng vai trò là một "màn hình hiển thị câm" (dumb terminal) siêu mượt, nhận nhiệm vụ thu thập và hiển thị, trong khi mọi tác vụ tính toán phức tạp nhất được di chuyển lên nền tảng đám mây chuyên biệt.

### 4.1. Lựa chọn Ngăn xếp Công nghệ (Tech Stack) và Căn cứ Kỹ thuật
Theo yêu cầu của tổ chức, quá trình phát triển giai đoạn 1 sẽ hoàn toàn tập trung vào nền tảng hệ điều hành Android, bỏ qua iOS. Việc lựa chọn công nghệ nhằm phục vụ hệ thống có tính chất xử lý dữ liệu nặng về toán học và chuỗi thời gian.

#### a. Mobile Client (Giao diện Điện thoại Android):
- **Ngôn ngữ & Kiến trúc UI**: Ngôn ngữ Kotlin kết hợp với Jetpack Compose. Jetpack Compose cho phép xây dựng UI dạng khai báo (declarative UI) và quản lý trạng thái luồng dữ liệu phức tạp. Điều này cực kỳ quan trọng để vẽ các đồ thị năng lượng uốn lượn (spline charts) và thực hiện các hoạt ảnh chuyển đổi mượt mà giữa các vùng nhịp sinh học mà các hệ thống UI dựa trên XML cũ không làm tốt.
- **Lớp Tương tác Thiết bị**: Sử dụng SDK `HealthConnectClient` do Google cung cấp để truy xuất dữ liệu sức khỏe thông qua cơ chế giao tiếp liên tiến trình (IPC) với ứng dụng trung tâm Health Connect. Sử dụng thư viện `Coroutines` và `WorkManager` để quản lý các tác vụ xử lý nền (background jobs), lập lịch đánh thức thiết bị định kỳ để thu thập và đồng bộ dữ liệu giấc ngủ, khắc phục các quy định nghiêm ngặt về quản lý pin của Android.

#### b. Backend Services (Dịch vụ Đám mây Trung tâm):
- **Ngôn ngữ xử lý**: Ngôn ngữ Python với framework `FastAPI`. Lý do nền tảng: FastAPI hỗ trợ mô hình bất đồng bộ `async/await`, hiệu năng phù hợp cho API độ trễ thấp, đồng thời tận dụng được hệ sinh thái khoa học dữ liệu và AI trưởng thành của Python để hiện thực hóa các bài toán y sinh.
- **Thư viện Toán học**: Sử dụng `NumPy` và `SciPy` làm lõi tính toán khoa học. `NumPy` phụ trách vector hóa dữ liệu chuỗi thời gian, còn `SciPy` cung cấp các công cụ giải phương trình vi phân, nội suy và tối ưu hóa cần thiết để hiện thực hóa mô hình Borbély và các bước hiệu chuẩn SNOP.
- **ORM & Database Driver**: Sử dụng `SQLAlchemy` để tương tác với PostgreSQL/TimescaleDB. Lớp truy cập dữ liệu nên tách rõ mô hình miền, truy vấn phân tích và thao tác ghi nhận chuỗi thời gian để thuận lợi cho bảo trì và kiểm thử.
- **Xử lý nền & Điều phối tác vụ**: Sử dụng `Celery` kết hợp `Redis` làm hàng đợi công việc. API FastAPI chỉ tiếp nhận yêu cầu, xác thực và tạo tác vụ; các phép tính nặng như tái tính toán biểu đồ năng lượng, hiệu chuẩn SNOP và tổng hợp dữ liệu nhiều ngày sẽ chạy bất đồng bộ ở worker riêng.

#### c. Lớp Cơ sở Dữ liệu (Database Tier):
- **Cơ sở dữ liệu Cốt lõi**: Hệ quản trị quan hệ PostgreSQL kết hợp với siêu tiện ích mở rộng TimescaleDB.
- Lý do: Ứng dụng theo dõi giấc ngủ tạo ra dữ liệu hoàn toàn mang tính chất chuỗi thời gian (time-series). TimescaleDB biến đổi PostgreSQL bằng cơ chế bảng ảo Hypertable, tự động phân vùng (auto-partitioning) dữ liệu theo không gian thời gian. Kiến trúc này mang lại ưu thế tuyệt đối: Tốc độ chèn dữ liệu (insert) duy trì ở mức ổn định ngay cả khi bảng đạt hàng tỷ dòng (nhanh hơn 15 lần so với PostgreSQL truyền thống). Nó hỗ trợ nén dạng cột giảm dung lượng đĩa lên tới 90% và cung cấp các hàm chuyên biệt như time_bucket() để tổng hợp chuỗi dữ liệu nhịp tim/giấc ngủ một cách chớp nhoáng.
- **Lớp Bộ nhớ đệm (Caching)**: Redis in-memory data store. Kết quả biểu đồ năng lượng hàng ngày của từng cá nhân sẽ được kết xuất dưới dạng cấu trúc tĩnh và lưu vào Redis để phản hồi siêu tốc mỗi khi người dùng mở lại App.

### 4.2. Thiết kế Lược đồ Cơ sở Dữ liệu Thời gian thực (Time-Series Database Schema)
Để đáp ứng cả yêu cầu về lưu trữ thông tin nghiệp vụ và dữ liệu chuỗi thời gian tần suất cao, lược đồ (schema) được phân tách thành các bảng thông tin (metadata tables) truyền thống và các bảng chuỗi thời gian phân vùng (hypertables). Các khóa ngoại (foreign keys) liên kết hai cấu trúc này.

#### Bảng 3: Thông tin Tài khoản và Định chuẩn (Metadata Table) - users
Bảng này lưu trữ thông tin trạng thái ít biến động của người dùng, đóng vai trò căn cứ thiết lập hệ số thuật toán.

| Tên Cột (Column) | Kiểu Dữ liệu (Data Type) | Ràng buộc (Constraints) | Mô tả & Chức năng |
|------------------|--------------------------|--------------------------|--------------------|
| `user_id` | UUID | PRIMARY KEY | Định danh duy nhất cho từng tài khoản hệ thống |
| `chronotype` | VARCHAR(50) | NOT NULL | Phân loại nhịp sinh học di truyền (Early Bird, Night Owl, Neutral) |
| `snop_hours` | DOUBLE PRECISION | DEFAULT 8.0 | Hằng số Nhu cầu Giấc ngủ tối ưu cá nhân hóa, được hiệu chuẩn liên tục |
| `current_sleep_debt` | DOUBLE PRECISION | DEFAULT 0.0 | Dữ liệu lưu trữ dư nợ giấc ngủ hiện tại (phút) để phản hồi API nhanh, cập nhật qua trigger |
| `created_at` | TIMESTAMPTZ | NOT NULL | Dấu thời gian tạo tài khoản |

#### Bảng 4: Kết quả Khảo sát (Metadata Table) - user_survey_responses
Bảng này lưu trữ các câu trả lời khảo sát để khởi tạo tham số thuật toán Seed Data.

| Tên Cột (Column) | Kiểu Dữ liệu (Data Type) | Ràng buộc | Mô tả |
|------------------|--------------------------|-----------|-------|
| `user_id` | UUID | FOREIGN KEY | Liên kết với bảng users |
| `question_id` | VARCHAR(50) | NOT NULL | Định danh câu hỏi (ví dụ: goal, health_issues, sleep_schedule) |
| `answer_key` | TEXT | NOT NULL | Giá trị câu trả lời hoặc JSON chứa thông tin chi tiết |

#### Bảng 5: Phiên Giấc ngủ (Hypertable) - sleep_sessions
Bảng này lưu trữ các khối thời gian giấc ngủ tổng quát. Nó đóng vai trò trực tiếp trong việc tính toán nợ giấc ngủ 14 ngày.

| Tên Cột (Column) | Kiểu Dữ liệu (Data Type) | Ràng buộc (Constraints) | Mô tả & Chức năng |
|------------------|--------------------------|--------------------------|--------------------|
| `session_id` | UUID | UNIQUE | Mã định danh riêng biệt của từng phiên ngủ |
| `user_id` | UUID | FOREIGN KEY | Tham chiếu liên kết đến bảng users |
| `start_time` | TIMESTAMPTZ | NOT NULL | Thời điểm bắt đầu ngủ (timestamp index) |
| `end_time` | TIMESTAMPTZ | NOT NULL | Thời điểm thức dậy hoàn toàn |
| `duration_mins` | INTEGER | NOT NULL | Tổng thời lượng ngủ thực tế (phút), loại trừ các lần tỉnh giữa chừng |
| `session_type` | VARCHAR(20) | NOT NULL | Phân loại: nightly (ngủ đêm) hoặc nap (ngủ trưa) |

*Lệnh Tối ưu hóa TimescaleDB*: Bảng này sẽ được chuyển đổi thành Hypertable dựa trên mốc thời gian bắt đầu ngủ.

```sql
SELECT create_hypertable('sleep_sessions', 'start_time');
```
#### Bảng 5: Sinh trắc học Tần suất cao (Hypertable) - biometric_data
Bảng này tiếp nhận khối lượng dữ liệu khổng lồ sinh ra từ các cảm biến vi mô liên tục (nhịp tim, nồng độ oxy, trạng thái giấc ngủ sâu/nông mỗi vài phút).

| Tên Cột (Column) | Kiểu Dữ liệu (Data Type) | Ràng buộc (Constraints) | Mô tả & Chức năng |
|------------------|--------------------------|--------------------------|--------------------|
| `user_id` | UUID | NOT NULL | Định danh người dùng. Không dùng khóa ngoại (FK constraint) để tối ưu hiệu suất ghi trên hypertable lớn |
| `time` | TIMESTAMPTZ | NOT NULL | Dấu thời gian ghi nhận dữ liệu tại một mili-giây cụ thể. Khóa phân vùng (partition key) |
| `metric_type` | VARCHAR(50) | NOT NULL | Cờ nhận diện loại dữ liệu: heart_rate_bpm, sleep_stage_rem, sleep_stage_deep |
| `value` | DOUBLE PRECISION | NOT NULL | Giá trị thực tế tại thời điểm đó (ví dụ: 65.5 bpm) |

*Lệnh Tối ưu hóa TimescaleDB*: Tốc độ phình to của bảng này yêu cầu cấu hình tự động phân vùng (chunking theo ngày) và nén dữ liệu kiểu cột mạnh mẽ, kết hợp với các truy vấn tập hợp liên tục (Continuous Aggregates) để làm mịn dữ liệu.

```sql
SELECT create_hypertable('biometric_data', 'time', chunk_time_interval => INTERVAL '1 day');
ALTER TABLE biometric_data SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'user_id, metric_type',
  timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('biometric_data', INTERVAL '7 days');
```

### 4.3. Luồng Kiến trúc Hệ thống Tổng thể (Architecture Flow)
Hệ thống hoạt động theo một vòng tuần hoàn khép kín, từ thiết bị người dùng lên đám mây và phản hồi ngược trở lại. Mô tả luồng dữ liệu từ quá trình thu thập thụ động đến lúc render biểu đồ trên thiết bị Android:

#### a. Thu thập và Tích lũy Cục bộ (Data Generation & On-Device Aggregation):
Suốt đêm, smartwatch, fitness band hoặc cảm biến chuyển động trên smartphone sẽ thu thập các chỉ số nhịp tim và trạng thái bất động của người dùng. Các ứng dụng phần cứng nội bộ của bên thứ 3 ghi các dữ liệu này vào Cổng trung tâm `Android Health Connect APK`. Dữ liệu lúc này nằm ở bộ nhớ nội bộ an toàn của thiết bị (On-Device Storage).

#### b. Khởi tạo Đồng bộ Hậu cảnh (Background Data Extraction):
Vào mỗi buổi sáng, ngay cả trước khi người dùng mở màn hình ứng dụng, hệ thống `WorkManager` của Android (được tích hợp trong app) sẽ nhận diện sự kết thúc của một giấc ngủ dài. Service chạy nền sẽ sử dụng `HealthConnectClient` thực hiện lời gọi hàm `readRecords()` với bộ lọc thời gian `TimeRangeFilter` từ lần đồng bộ cuối cùng. Các bản ghi `SleepSessionRecord` được trích xuất, làm phẳng (flattened) và đóng gói thành một cấu trúc JSON thống nhất.

#### c. Tiếp nhận Đám mây và Điều phối tác vụ (Cloud Ingestion & Task Dispatch):
Gói JSON được truyền tải qua HTTPS TLS 1.3 đến API Gateway của hệ thống Backend viết bằng `FastAPI`. Tại đây, Gateway làm nhiệm vụ kiểm tra bảo mật JWT (JSON Web Token) để xác thực người dùng, chuẩn hóa payload và ghi nhanh các bản ghi bắt buộc xuống PostgreSQL/TimescaleDB. Sau đó, hệ thống tạo các tác vụ `Celery` để xử lý các bước nặng về tổng hợp và tái tính toán mà không khóa vòng đời request-response của API.

#### d. Xử lý và Lưu trữ Chuỗi thời gian (Storage Worker):
Các `Celery workers` liên tục nhận tác vụ từ `Redis`, tách siêu dữ liệu, thực hiện thao tác `INSERT` theo lô vào các hypertables `sleep_sessions` và `biometric_data`, đồng thời chuẩn hóa dữ liệu trùng lặp hoặc chồng lấp từ nhiều thiết bị. Việc tách worker ghi dữ liệu và worker tính toán giúp hệ thống chịu tải tốt hơn ở khung giờ đồng bộ buổi sáng.

#### e. Công cụ Tính toán Toán học (Analytics & Algorithm Engine):
Sau khi dữ liệu được lưu thành công, hệ thống kích hoạt `Python Analytics Engine`. Engine này sử dụng `NumPy` để xử lý vector thời gian, `SciPy` để giải các phép tính vi phân cho Process S và Process C, và xuất ra chuỗi tọa độ `(x, y)` cho 24 giờ tiếp theo. Kiến trúc này cho phép mở rộng thuận lợi sang các mô hình dự báo nâng cao hoặc các pipeline AI trong giai đoạn sau.

#### f. Lưu trữ Bộ đệm và Hiển thị (Caching & UI Rendering):
Chuỗi tọa độ năng lượng vừa được tổng hợp sẽ được tuần tự hóa (serialized) và lưu trực tiếp vào Redis Cache, gán với key là `user_id` và thời gian tồn tại (TTL) là 24 giờ. Cùng lúc đó, khi người dùng vừa pha xong cà phê và mở ứng dụng, màn hình Android Compose lập tức gọi API GET đến hệ thống. Backend `FastAPI` ưu tiên đọc dữ liệu từ Redis để phản hồi dưới 50 ms; nếu cache chưa sẵn sàng, API trả về bản gần nhất kèm trạng thái đang tái tính toán để tránh treo giao diện.

### 4.4. Triển khai Logic Thuật toán Nhịp sinh học trên Hệ thống Python
Chất lượng của giải pháp nằm ở việc mã hóa chính xác các mô hình lý thuyết khoa học thành các mô-đun Python có khả năng kiểm thử và mở rộng tốt. Hệ thống Python Backend chạy chu trình tái tính toán (re-calibration) theo 4 bước tuần tự.

#### Bước 1: Tính toán Khối lượng Nợ giấc ngủ cấp tính (Sleep Debt Aggregation)
Hệ thống truy xuất dữ liệu từ hypertable `sleep_sessions` và bảng `user_survey_responses`. Thuật toán ưu tiên sử dụng dữ liệu thực nghiệm (Health Connect). Nếu dữ liệu lịch sử chưa đủ 14 ngày, hệ thống sử dụng kết quả khảo sát (Seed Data) để nội suy giá trị SNOP và pha sinh học khởi điểm. Khối xử lý này chạy trong `Celery worker`, cho phép gom nhiều phép tổng hợp và cập nhật cache mà không ảnh hưởng API thời gian thực.

#### Bước 2: Xây dựng Đường cong Áp lực Nội môi (Process S Modeler)
Sử dụng `NumPy` hoặc `SciPy` để tính toán sự tích tụ Adenosine:
$H(t) = 1 - (1 - H(t_0)) \cdot e^{\frac{-(t-t_0)}{18.2}}$

#### Bước 3: Xây dựng Đường cong Nhịp sinh học (Process C Modeler)
Triển khai phương trình 5 sóng hài bằng các hàm `numpy.sin`, `numpy.pi` và các phép toán vector hóa. Việc sử dụng mảng số thực dấu phẩy động của `NumPy` đảm bảo độ chính xác cần thiết cho các phép tính y sinh, đồng thời giảm chi phí xử lý khi phải sinh ra 1.440 điểm dữ liệu mỗi ngày cho mỗi người dùng.

#### Bước 4: Hợp nhất và Thiết lập Hệ thống Cảnh báo (Synthesis & Nudge Scheduling)
Sử dụng mảng `NumPy` để lưu trữ 1.440 điểm năng lượng, sau đó áp dụng các bước hậu xử lý bằng Python nhằm tìm điểm cực trị, phân lớp các vùng năng lượng và sinh lịch cảnh báo. Kết quả cuối cùng được đóng gói thành JSON tối giản để lưu cache Redis và phục vụ phản hồi API siêu tốc.
