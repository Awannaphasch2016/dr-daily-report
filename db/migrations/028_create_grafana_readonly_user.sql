-- Migration 028: Create read-only MySQL user for Grafana
-- Security: SELECT-only access to ticker_data database
--
-- Execute via SSM tunnel:
--   1. Start tunnel:
--      aws ssm start-session --target i-0dab21bdf83ce9aaf \
--        --document-name AWS-StartPortForwardingSessionToRemoteHost \
--        --parameters '{"host":["dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com"],"portNumber":["3306"],"localPortNumber":["3307"]}' \
--        --region ap-southeast-1
--
--   2. Connect:
--      mysql -h 127.0.0.1 -P 3307 -u admin -p ticker_data
--
--   3. Run this SQL with <GRAFANA_MYSQL_PASSWORD> replaced by actual password

CREATE USER IF NOT EXISTS 'grafana_readonly'@'%' IDENTIFIED BY '<GRAFANA_MYSQL_PASSWORD>';
GRANT SELECT ON ticker_data.* TO 'grafana_readonly'@'%';
FLUSH PRIVILEGES;
