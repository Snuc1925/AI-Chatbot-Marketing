1) Tri thức chung 
    + Khi user hỏi campaign mời gói thì tương ứng report_offer_detail_isdn.action_channel = "SMS", khi user hỏi campaign clicklink thì tương ứng action_channel = "notify". Action_channel là loại campaign.
    + Hầu hết tất cả các câu hỏi trong kịch bản cần xác định rõ là hỏi trong những campaign nào (hoặc có thể là toàn bộ (tất cả) các campaign có trong hệ thống), khoảng thời gian nào

2) Xác định tỉ lệ nhắn tin (tỉ lệ gửi) thành công, KHÁC với tỉ lệ nhận tin và phản hồi: 
    + Số lượt gửi thành công: select count(isdn)from report_offer_detail_isdn where is_success_action = 1
    + Tổng lượt gửi: select count(isdn) from report_offer_detail_isdn

3) Xác định tỉ lệ phản hồi: 
Xác định xem campaign mà user đề cập là thuộc về campaign mời gói (action_channel = 'SMS') hay là campaign click link (action_channel = 'notify')
+ Campaign mời gói: Tỷ lệ phản hồi = Số thuê bao mua đúng gói/Số thuê bao nhận tin thành công × 100%.

Số thuê bao mua đúng gói = select count(distinct isdn) from report_offer_detail_isdn where action_channel='SMS' and campaign_register_number=1

Số thuê bao nhận tin thành công: select count(distinct isdn) from report_offer_detail_isdn where action_channel='SMS' and is_success_action=1

+ Campaign click link: Tỷ lệ phản hồi = Số thuê bao click link duy nhất/Số thuê bao nhận tin thành công × 100%.

Số thuê bao click link :select count(distinct isdn) from report_offer_detail_isdn where action_channel='notify' and campaign_register_number=1

Số thuê bao nhận tin thành công:select count(distinct isdn) from report_offer_detail_isdn where action_channel='notify' and is_success_action=1

4) Độ tuổi, giới tính có tỷ lệ phản hồi Campaign cao nhất
Format trả lời:
“Trong phạm vi <Campaign/Gói/Toàn bộ Campaign> và KHoảng thời gian <Thời gian>:
- Nhóm tuổi có tỷ lệ phản hồi cao nhất: <Nhóm tuổi>, đạt <A>% (<B>/<C> thuê bao).
- Giới tính có tỷ lệ phản hồi cao nhất: <Nam/Nữ>, đạt <D>%.

Loại campaign where action_channel=
Campaign <Tên Campaign>: where campaign_id = ''

Tùy thuộc vào loại campaign để xác định tỷ lệ phản hồi

<D> thuê bao mua đúng gói: select count(distinct isdn), cust_age from (select * from report_offer_detail_isdn where action_channel='SMS' +campaign_register_number= 1 and campaidn_ai_id = X and partition ...) join  (select isdn cust_age fron f_adpm_aimkt_campaign_customer_detail)  on a.isdn = b.isdn group by cust_age
Số thuê bao nhận tin thành công: select count(distinct isdn), cust_age from (select * from report_offer_detail_isdn where action_channel='SMS' and is_success_action=1 and campaidn_ai_id = X and partition ...)  join  (select isdn cust_age fron f_adpm_aimkt_campaign_customer_detail)  on a.isdn = b.isdn group by cust_age
Tỷ lệ phản hồi = Số thuê bao mua đúng gói/Số thuê bao nhận tin thành công × 100%.

* <F> thuê bao click link :select count(distinct isdn), cust_age from (select * from report_offer_detail_isdn where action_channel='notify' +campaign_register_number= 1 and campaidn_ai_id = X and partition ...) join  (select isdn cust_age fron f_adpm_aimkt_campaign_customer_detail)  on a.isdn = b.isdn group by cust_age
Số thuê bao nhận tin thành công:select count(distinct isdn), cust_age from (select * from report_offer_detail_isdn where action_channel='notify' and is_success_action=1 and campaidn_ai_id = X and partition ...)  join  (select isdn cust_age fron f_adpm_aimkt_campaign_customer_detail)  on a.isdn = b.isdn group by cust_age


5) Với nhóm tuổi ../giới tính../khu vực Gói nào có hiệu quả phản hồi cao nhất
Tỷ lệ phản hồi theo kênh group by action_channel
Giới tính, khu vực tìm trong bảng f_adpm_aimkt_campaign_customer_detail

6) Với nhóm tuổi ../giới tính../khu vực Gói nào có hiệu quả phản hồi cao nhất
thuê bao mua đúng gói: select count(distinct isdn), promotion_package from report_offer_detail_isdn where campaign_register_number= 1+ campaign + ktgian group by promotion_package 
Số thuê bao nhận tin thành công: select count(distinct isdn), promotion_package  from report_offer_detail_isdn where  is_success_action=1 + campaign + partition group by promotion_package 