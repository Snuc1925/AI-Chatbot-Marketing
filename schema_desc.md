* f023_mpre_vas: Đây là bảng log mua gói
- topic_kafka: ADD_MONEY, 2G3G, VTFREE, DATAPLUS, GOOGLE_DCB_REFUND, BI_CDR_SPLUS, ITALK, CHARGINGGW, AUTODETECTZONE
- filename: vtfree.0001.txt
- prd_id: 20260731, 20260801, null
- hour_id: 00->23
- import_date: 20260801
- headnum_no: 1 số nào đó
- isdn:
- vas_type: VIETTEL, HUYSMS170, DK_OTHER, REFUND, 2G3G, SPUD, VTFREE, VCONNECT, HUYFT109
- vas_service: HUY T15K, HUY KM49, HUY S3, HUY DT38, HUY FT5, SMARTMOTO, AIRTIME_CHARGE, HUY T15D, HUY DK30, HUY MP120S, CALLPLUS_FEE_EXT, HUY MP90X, DK_OTHER, MPBX, HUY MP70, 2G3G, VTFREE, HUY S20, CALLPLUS_FEE_INT, UNG_TIEN, HUY FT3S, HUY S30
- sub_service: 990 giá trị: HGG100, CT50, DT50, MT10, DT50K, 5G150, FB5K, MWG160, TQ10, SD30S, HUY T15K, ....
- action_no: KT, DK
- action_no2: null 
- vas_status: null
- command: KTS5, FT5, VT100, 
- command2: 
- charge_type: -1, 1, ""
- sta_datetime: date
- org_charge: float
- prom_charge: float
- tot_charge: float
- party_code: VIETTEL_VCRBT_RENEW_....., PC_DATA_EXTEND@ST7K@191@191@191
- description: S5, VT100, MP5X, 191, Tru phi gia han goi 5G10
- source_name: VTFREE, DATAPLUS, TTVAS_VTT, 
- direction_id: 3.0000, 4.0000
- insert_date: date
- mm_charge: 
- mon: 2608
- partition: 20260801


* webservice_log_v2: Bảng 
- isdn: (string) 84917568540
- campaign_action_id: 44897, ...
- webservice: 1549, 1530, ... 
- url: http://10:208.59.202:8556/eventws?wsdl
- request_time: 20260703200444 (năm tháng ngày giờ phút giây)
- request: 
<mã <xml>, ví dụ: \"body"\: \"Đăng ký 5GVS12 chỉ 12000đ/ngày, nhận 6GB data"....
- response_time: thời gian: 20260703200444
- response: 
<?xml version ?>###
<S: envelope xmlns:S=>
<...>
- status: 1, 4, 5, TIMEOUT
- campaign_id: vd: 101471,...
- filed1: NULL
- mode: TEST, ONLINE
- partition: 20260703


* sms_log_v2
- msisdn: (string) tương tự với isdn (cái này là số điện thoại)
- action_id: 41009, 42001, 42009, 41007, ...
- sender: VIETTEL_KM
- send_time: 20250919174500
- status: -1007M, 0 (0 là status truyền thông thành công)
- gateway: -1000 nếu status là âm thì gateway âm, = -1000, nếu status = 0 thì gateway dương
- duration: null
- transaction_id: null
- campaign_id: 99080
- history_id: nếu như status = 0 thì history_id = 186, ngược lại thì null
- type: null
- partition: 20250919

* f_adpm_aimkt_campaign_customer_detail:
- msisdn 
- program_code: mxh_high&wifi_partial&p2, mxh_low@wifi_partial&p2, mxh_high&not_wifi&p2
- vas_name: 5G50, MT7Z, 5GMAX, 5G70
- channel: MYVIETTEL, SMS, CALLBOT
- event_time: 10h, 16h, 21h,...
- cdr_name: PTDL 
- group_flag: TG, CONTROL
- cust_age: gồm 5 giá trị: hoc sinh, sinh vien, lao dong tre, trung nien, cao tuoi. 
- province_code_home: HCM, CTO, SLA, QNI, HUE, CMU, HNI
- trangthai_truyenthong: tttc, ko_tttc
- promo_label: null
- chu_ky_goi: null
- price: null
- tieu_dung_chinh: null
- ten_usecase: không gói vào gói 5 tỉnh
- partition: 20260810

