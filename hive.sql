CREATE EXTERNAL TABLE `f023_mpre_vas` (
  `topic_kafka` string,
  `filename` string,
  `prd_id` string,
  `hour_id` string,
  `import_date` string,
  `headnum_no` string,
  `isdn` string,
  `vas_type` string,
  `vas_service` string,
  `sub_service` string,
  `action_no` string,
  `action_no2` string,
  `vas_status` string,
  `command` string,
  `command2` string,
  `charge_type` string,
  `sta_datetime` string,
  `org_charge` string,
  `prom_charge` string,
  `tot_charge` string,
  `party_code` string,
  `description` string,
  `source_name` string,
  `direction_id` string,
  `insert_date` string,
  `mm_charge` string
)
PARTITIONED BY (`mon` string, `partition` string);

CREATE EXTERNAL TABLE `sms_log_v2` (
  `msisdn` string,
  `campaign_action_id` string,
  `sender` string,
  `send_time` string,
  `status` string,
  `gateway` string,
  `duration` string,
  `transaction_id` string,
  `campaign_id` string,
  `history_id` string,
  `mode` string
)
PARTITIONED BY (`partition` string);

CREATE TABLE `f_adpm_aimkt_campaign_customer_detail` (
  `msisdn` string,
  `program_code` string,
  `vas_name` string,
  `channel` string,
  `event_time` string,
  `cdr_name` string,
  `group_flag` string,
  `cust_age` double,
  `province_code_home` string,
  `trangthai_truyenthong` string,
  `promo_label` string,
  `chu_ky_goi` string,
  `price` double,
  `tieu_dung_chinh` double,
  `ten_usecase` string
)
PARTITIONED BY (`partition` string);

CREATE EXTERNAL TABLE `webservice_log_v2` (
  `isdn` string,
  `campaign_action_id` string,
  `webservice` string,
  `url` string,
  `request_time` string,
  `request` string,
  `response_time` string,
  `response` string,
  `status` string,
  `campaign_id` string,
  `filed1` string,
  `mode` string
)
PARTITIONED BY (`partition` string);