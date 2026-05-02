workspace "Daily Report Platform" "Auto-generated architecture from infrastructure sync" {

    model {
        # External Actors
        telegramUsers = person "Telegram Bot Users" "End users accessing ticker analysis through Telegram Mini App"

        # External Systems
        telegramPlatform = softwareSystem "Telegram Platform" "Official Telegram Bot API"
        openRouter = softwareSystem "OpenRouter API" "LLM API gateway"
        yahooFinance = softwareSystem "Yahoo Finance API" "Market data provider"
        langfuse = softwareSystem "Langfuse" "LLM observability platform"

        # Main System
        dailyReportSystem = softwareSystem "Daily Report System" "Ticker analysis platform" {

            dr_daily_report_fund_data_sync_dev_lambda = container "dr-daily-report-fund-data-sync-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_get_report_list_dev_lambda = container "dr-daily-report-get-report-list-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_get_ticker_list_dev_lambda = container "dr-daily-report-get-ticker-list-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_line_bot_dev_lambda = container "dr-daily-report-line-bot-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_pattern_precompute_dev_lambda = container "dr-daily-report-pattern-precompute-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_pdf_worker_dev_lambda = container "dr-daily-report-pdf-worker-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_precompute_controller_dev_lambda = container "dr-daily-report-precompute-controller-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_query_tool_dev_lambda = container "dr-daily-report-query-tool-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_report_worker_dev_lambda = container "dr-daily-report-report-worker-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_schema_manager_dev_lambda = container "dr-daily-report-schema-manager-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_slack_notifier_dev_lambda = container "dr-daily-report-slack-notifier-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda (python3.11)"
            }
            dr_daily_report_static_api_generator_dev_lambda = container "dr-daily-report-static-api-generator-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_telegram_api_dev_lambda = container "dr-daily-report-telegram-api-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_ticker_fetcher_dev_lambda = container "dr-daily-report-ticker-fetcher-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            dr_daily_report_ticker_scheduler_dev_lambda = container "dr-daily-report-ticker-scheduler-dev (Lambda)" "Lambda function" {
                technology "AWS Lambda ()"
            }
            aurora_db = container "aurora (Database)" "Database" {
                technology "aurora-mysql Database"
            }
            dr_daily_report_telegram_api_dev_gateway = container "dr-daily-report-telegram-api-dev (API Gateway)" "API Gateway" {
                technology "AWS API Gateway (HTTP)"
            }
            line_bot_pdf_reports_755283537543_bucket = container "line-bot-pdf-reports-755283537543 (S3)" "Storage" {
                technology "AWS S3"
            }
            dr_daily_report_static_api_dev_bucket = container "dr-daily-report-static-api-dev (S3)" "Storage" {
                technology "AWS S3"
            }
            dr_daily_report_webapp_dev_bucket = container "dr-daily-report-webapp-dev (S3)" "Storage" {
                technology "AWS S3"
            }
        }

        # Basic relationships (would be enhanced with actual dependency analysis)
        telegramUsers -> telegramPlatform "Uses"
        telegramPlatform -> dailyReportSystem "Integrates with"
    }

    views {
        systemContext dailyReportSystem "SystemContext" {
            include *
            autoLayout
        }

        container dailyReportSystem "Containers" {
            include *
            autoLayout
        }
    }
}