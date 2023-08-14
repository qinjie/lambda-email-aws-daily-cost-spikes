import boto3
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv

AWS_REGION = "us-east-1" # Must be us-east-1 region

load_dotenv()
EMAIL_SUBJECT = os.getenv('EMAIL_SUBJECT', '')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
TO_EMAILS = os.getenv('TO_EMAILS', '')
CC_EMAILS = os.getenv('CC_EMAILS', '')

MAX_DATA_POINTS = int(os.getenv('MAX_DATA_POINTS', 20))      # Examine max 20 data points
MAX_PERIOD_HOURS = int(os.getenv('MAX_PERIOD_HOURS', 120))    # Examine only data in last 120 hours (5 days)
THRESH_INCREMENT_PERCENT = int(os.getenv('THRESH_INCREMENT_PERCENT', 5))    # Alert if any datapoint change is >+10%
THRESH_INCREMENT_DOLLAR = int(os.getenv('THRESH_INCREMENT_DOLLAR', 200))     #   or >+$200 within the examing period
MIN_ALERT_COST = int(os.getenv('MIN_ALERT_COST', 100))                       # Only alert if cost at datapoint is >$100
ONLY_OVERALL_COST = os.getenv('ONLY_OVERALL_COST','').lower() == 'true'      # Only check on overall cost


def find_alarming_costs():
    
    client = boto3.client('cloudwatch', region_name=AWS_REGION)
    
    response = client.list_metrics(Namespace='AWS/Billing', MetricName='EstimatedCharges')
    metrics = response.get('Metrics')
    print(f'Total {len(metrics)} Metrics')
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours = MAX_PERIOD_HOURS)
    
    all_costs = []
    alarming_costs = []
    for metric in metrics:
        dimensions = metric.get('Dimensions', [])
        if not dimensions: continue
    
        # Ignore linked account data if ONLY_OVERALL_COST = True
        is_linked_account = [d.get('Name','')=='LinkedAccount' for d in dimensions]
        if ONLY_OVERALL_COST and sum(is_linked_account) > 0: continue
    
        d_names = [d.get('Value') for d in dimensions]
        label = '_'.join(d_names)

        response = client.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'estimated_charge',
                    'MetricStat': {
                        'Metric': {
                            "Namespace": "AWS/Billing",
                            "MetricName": "EstimatedCharges",
                            'Dimensions': dimensions
                        },
                        'Period': 6*60*60,
                        "Stat": "Maximum"
                    },
                    'Label': label,
                    'ReturnData': True,
                },
            ],
            StartTime=start_time,
            EndTime=end_time,
            ScanBy='TimestampDescending',
            MaxDatapoints=MAX_DATA_POINTS
        )
    
        metric = response['MetricDataResults'].pop() if response['MetricDataResults'] else None
    
        # Ignore 0 value datapoints or if max datapoint is less than MIN_ALERT_COST
        if sum(metric.get('Values', [])) <= 0 or max(metric.get('Values', [])) <= MIN_ALERT_COST: continue
        
        # Arrange costs as a list of (timestamp, value, label) so that they can be saved into CSV if needed
        timestamps = [ts.strftime('%Y-%m-%dT%H:%M:%SZ') for ts in metric['Timestamps']]
        rows = list(zip(timestamps, metric['Values'], [label]*len(metric['Timestamps'])))
        # Sort the values by ascending timestamp
        rows.sort()
        
        # Find the dollar changes or percentage changes between data points
        unzipped = list(zip(*rows))
        costs = unzipped[1]
        cost_changes = [t - s for s, t in zip(costs, costs[1:])]
        cost_changes_percent = [(t - s)/s*100 for s, t in zip(costs, costs[1:]) if s > MIN_ALERT_COST]
        
        # Alert if changes exceed threshold values
        print('Change in dollar & percentage:', label, round(max(cost_changes)), f'{round(max(cost_changes_percent),2)}%')
        if max(cost_changes) > THRESH_INCREMENT_DOLLAR or max(cost_changes_percent) > THRESH_INCREMENT_PERCENT:
            print('     ^^^^^^^   Alert   ^^^^^^^^')
            alarming_costs.extend(rows)
    
    return alarming_costs
        
        
def send_alert_email(data):
    ses_client = boto3.client('ses')
    
    # Check sender_email is verified
    response = ses_client.list_identities()
    if SENDER_EMAIL not in response.get('Identities', []):
        # Send verification email
        response = ses_client.verify_email_address(
            EmailAddress=SENDER_EMAIL
        )
        # Exit from lambda function
        raise Exception(f'Sender {SENDER_EMAIL} not verified. Verification email is sent.')
    
    to_emails = TO_EMAILS.split(';')
    cc_emails = CC_EMAILS.split(';')
    trs = []
    for row in data:
        trs.append(f'<tr><td>{row[2]}</td><td>{row[0]}</td><td>{row[1]}</td></tr>')

    msg_html = f'<table border="1"><tr><th>Service</th><th>Timestamp</th><th>Cost</th></tr>{"".join(trs)}</table>'

    # Optional
    msg_text = json.dumps(data)
    reply_to_emails = [SENDER_EMAIL]
    
    print(f'Sending email to {to_emails}')
    response = ses_client.send_email(
        Source=SENDER_EMAIL,
        Destination={
            'ToAddresses': to_emails,
            'CcAddresses': cc_emails
        },
        Message={
            'Subject': {
                'Data': EMAIL_SUBJECT,
            },
            'Body': {
                'Text': {
                    'Data': msg_text,
                },
                'Html': {
                    'Data': msg_html,
                }
            }
        },
        ReplyToAddresses=reply_to_emails
    )



def lambda_handler(event, context):
    alarming_costs = find_alarming_costs()
    # Send alert if alarming_costs is not empty
    if alarming_costs:
        print(alarming_costs)
        send_alert_email(data=alarming_costs)
    else:
        print('No alarming cost change found')


if __name__ == '__main__':
    lambda_handler(None, None)
