# Lambda Email AWS Daily Cost Alert

To avoid cost shock at the end of the month, AWS provides [Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html) and [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) to monitor and get alerted on abnormal cost changes. This lambda is another tools for the same purpose.

This lambda function pulls the estimated costs for all services from AWS CloudWatch. For costs which match the filters, it will list their costs and sends alert emails.



### Pre-requites

1. Enable billing alert by going to https://console.aws.amazon.com/billing/, Billing Preferences > Alert preference; Choose Edit; Choose Receive CloudWatch Billing Alerts.
2. Sender email address must be verified in the AWS SES.

### Setup
1. Download required libraries in `requirements.txt` into `python` folder
    ```
    pip install -r requirements.txt --target python
    ```
2. Zip the folder content for deployment in Lambda function.
3. Create lambda function using the zip file.
4. Setup necessary environment variables according to `.env` file.
5. Grant lambda execution role with permissions to access RDS and SES.
6. Use Eventbridge to schedule the lambda function to run daily.




### Reference

https://repost.aws/knowledge-center/cloudwatch-estimatedcharges-alarm
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html#turning_on_billing_metrics
https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html
