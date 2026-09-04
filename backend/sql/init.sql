CREATE DATABASE IF NOT EXISTS default;

CREATE TABLE IF NOT EXISTS default.f023_mpre_vas_manh (
    topic_kafka Nullable(String),
    filename Nullable(String),
    prd_id Nullable(UInt32),
    hour_id Nullable(String),
    import_date Nullable(Date),
    headnum_no Nullable(String),
    isdn String,
    vas_type Nullable(String),
    vas_service Nullable(String),
    sub_service Nullable(String),
    action_no Nullable(String),
    action_no2 Nullable(String),
    vas_status Nullable(String),
    command Nullable(String),
    command2 Nullable(String),
    charge_type Nullable(String),
    sta_datetime Nullable(DateTime),
    org_charge Nullable(Float64),
    prom_charge Nullable(Float64),
    tot_charge Nullable(Float64),
    party_code Nullable(String),
    description Nullable(String),
    source_name Nullable(String),
    direction_id Nullable(Float64),
    insert_date Nullable(DateTime),
    mm_charge Nullable(Float64),
    mon Nullable(String),
    partition UInt32
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, isdn);

CREATE TABLE IF NOT EXISTS default.webservice_log_v2_manh (
    isdn String,
    campaign_action_id Nullable(UInt64),
    webservice Nullable(String),
    url Nullable(String),
    request_time String,
    request Nullable(String),
    response_time Nullable(String),
    response Nullable(String),
    status Nullable(String),
    campaign_id Nullable(UInt64),
    filed1 Nullable(String),
    mode Nullable(String),
    partition UInt32
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, isdn, request_time);

CREATE TABLE IF NOT EXISTS default.sms_log_v2 (
    msisdn String,
    action_id Nullable(UInt64),
    sender Nullable(String),
    send_time String,
    status Nullable(String),
    gateway Nullable(Int64),
    duration Nullable(Int64),
    transaction_id Nullable(String),
    campaign_id Nullable(UInt64),
    history_id Nullable(String),
    type Nullable(String),
    partition UInt32
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, msisdn, send_time);

CREATE TABLE IF NOT EXISTS default.f_adpm_aimkt_campaign_customer_detail (
    msisdn String,
    program_code Nullable(String),
    vas_name Nullable(String),
    channel Nullable(String),
    event_time Nullable(String),
    cdr_name Nullable(String),
    group_flag Nullable(String),
    cust_age Nullable(String),
    province_code_home Nullable(String),
    trangthai_truyenthong Nullable(String),
    promo_label Nullable(String),
    chu_ky_goi Nullable(String),
    price Nullable(Float64),
    tieu_dung_chinh Nullable(String),
    ten_usecase Nullable(String),
    partition UInt32
) ENGINE = MergeTree()
PARTITION BY partition
ORDER BY (partition, msisdn);

INSERT INTO default.f_adpm_aimkt_campaign_customer_detail (msisdn, program_code, vas_name, channel, event_time, cdr_name, group_flag, cust_age, province_code_home, trangthai_truyenthong, ten_usecase, partition) VALUES ('84981234567', 'mxh_high&wifi_partial&p2', '5G50', 'SMS', '10h', 'PTDL', 'TG', 'lao dong tre', 'HNI', 'tttc', 'không gói vào gói 5 tỉnh', 20260810), ('84987654321', 'mxh_high&wifi_partial&p2', '5G50', 'SMS', '10h', 'PTDL', 'TG', 'sinh vien', 'HCM', 'tttc', 'không gói vào gói 5 tỉnh', 20260810), ('84912345678', 'mxh_low@wifi_partial&p2', '5G70', 'MYVIETTEL', '16h', 'PTDL', 'TG', 'trung nien', 'CTO', 'tttc', 'không gói vào gói 5 tỉnh', 20260810), ('84976543210', 'mxh_low@wifi_partial&p2', '5GMAX', 'CALLBOT', '21h', 'PTDL', 'TG', 'cao tuoi', 'SLA', 'tttc', 'không gói vào gói 5 tỉnh', 20260810), ('84988888888', 'mxh_high&not_wifi&p2', 'MT7Z', 'SMS', '10h', 'PTDL', 'CONTROL', 'hoc sinh', 'QNI', 'ko_tttc', 'không gói vào gói 5 tỉnh', 20260810);

INSERT INTO default.sms_log_v2 (msisdn, action_id, sender, send_time, status, gateway, campaign_id, history_id, partition) VALUES ('84981234567', 41009, 'VIETTEL_KM', '20260810100500', '0', 1000, 99080, '186', 20260810), ('84987654321', 41009, 'VIETTEL_KM', '20260810100500', '0', 1000, 99080, '186', 20260810), ('84988888888', 41009, 'VIETTEL_KM', '20260810100500', '-1007M', -1000, 99080, NULL, 20260810);

INSERT INTO default.webservice_log_v2_manh (isdn, campaign_action_id, webservice, request_time, status, campaign_id, mode, partition) VALUES ('84912345678', 44897, '1549', '20260810160200', '1', 101471, 'ONLINE', 20260810), ('84976543210', 44898, '1530', '20260810210500', '200', 101472, 'ONLINE', 20260810);

INSERT INTO default.f023_mpre_vas_manh (isdn, vas_type, vas_service, sub_service, action_no, sta_datetime, tot_charge, description, partition) VALUES ('84981234567', 'VIETTEL', '5G50', '5G50', 'DK', '2026-08-10 10:35:00', 50000.0, 'Đăng ký gói 5G50', 20260810), ('84912345678', 'VIETTEL', '5G70', '5G70', 'DK', '2026-08-10 16:45:00', 70000.0, 'Đăng ký gói 5G70', 20260810);