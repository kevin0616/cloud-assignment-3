import json
import boto3
import datetime
import urllib.request
import base64
import os

rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')

host = 'https://search-photos-yeglk7r5keywwpjplxo7lju5z4.aos.us-east-1.on.aws'
index = 'photos'
username = 'kevin0616'
password = 'Sieun$200181'

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    print('index lambda triggered')
    print('event: ', event)

    s3_response = s3.get_object(Bucket=bucket, Key=key)
    raw_content = s3_response['Body'].read()

    try:
        image_bytes = base64.b64decode(raw_content, validate=True)
    except Exception:
        image_bytes = raw_content

    # 1. Rekognition
    response = rekognition.detect_labels(
        Image={'Bytes': image_bytes},
        MaxLabels=10
    )
   
    labels = [label['Name'].lower() for label in response['Labels']]

    # 2. Get custom metadata and combine
    head = s3.head_object(Bucket=bucket, Key=key)
    metadata = head.get('Metadata', {})
    
    custom_labels = []
    if 'customlabels' in metadata:
        custom_labels = metadata['customlabels'].split(',')
    
    all_labels = list(set(labels + custom_labels))
    print('all_labels: ', all_labels)

    # 3. JSON document
    document = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": datetime.datetime.now().isoformat(),
        "labels": all_labels
    }

    # 4. Index to OpenSearch
    url = f"{host}/{index}/_doc/{key}"
    payload = json.dumps(document).encode('utf-8')
    auth_str = f"{username}:{password}"
    encoded_auth = base64.b64encode(auth_str.encode('ascii')).decode('ascii')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_auth}'
    }

    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method='PUT'
    )

    try:
        with urllib.request.urlopen(req) as response:
            print("Indexed:", response.read().decode("utf-8"))
    except Exception as e:
        print(f"OpenSearch Error: {e}")

    print("Finished")
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': '*',
        },
        'body': json.dumps('Indexed success2.0!')
    }