- Xác định số lượt gửi thành công
Tỉ lệ nhắn tin thành công = Số lượt gửi thành công / Tổng lượt gửi * 100 % 
Trong đó: Số lượt gửi thành công xác định như sau đối với các kênh: 
	+ sms: Bảng sms_log_v2 (status = 0)
	+ myvt: Bảng webservice_log_v2 (status = 1)
	+ callbot: Bảng webservice_log_v2 (status = 200)

- Xác định số thuê bao phản hồi (mua gói)
Join bảng f_adpm_aimkt_campaign_customer_detail với 2 bảng ghi log truyền thông theo kênh (sms_log_v2 với sms, webservice_log_v2 với myvt, callbot) bằng isdn để ra được tập thuê bao được truyền thông thành công rồi join tiếp với bảng f023_mpre_vas để check xem thuê bao có mua gói hay không. 

- Xác định số thuê bao mua đúng offer qua kênh khuyến nghị và qua kênh khác: 
Hiện tại bảng f023_mpre_vas không có trường để xác định được cụ thể thuê bao mua gói qua kênh nào. Nên đang tính là nếu thuê bao được khuyến nghị kênh nào mà có log mua gói thì sẽ tính luôn cho kênh đó.

- Xác định thời gian phản hồi
Thời gian phản hồi = Thời điểm phản hồi đầu tiên − Thời điểm nhận tin thành công.

- Tri thức về tỉnh thành: 
HCM: Hồ chí Minh
CTO: Cần Thơ
SLA: Sơn La
QNI: Quảng Ninh
HUE: Huế
CMU: Cà Mau
HNI: Hà Nội
