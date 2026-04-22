import json
import boto3
import urllib.request
import base64

host = 'https://search-photos-yeglk7r5keywwpjplxo7lju5z4.aos.us-east-1.on.aws'
index = 'photos'
username = 'kevin0616'
password = 'Sieun$200181'

lex_client = boto3.client('lexv2-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    print("event: ", event)
    
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*"
            },
            "body": ""
        }
    
    query = event['queryStringParameters']['q']

    lex_response = lex_client.recognize_text(
        botId='4MBMXLSLWA',
        botAliasId='TSTALIASID',
        localeId='en_US',
        sessionId='session',
        text=query
    )

    keywords = []

    try:
        intent = lex_response['sessionState']['intent']
        slots = intent['slots']

        if slots and 'Labels' in slots and slots['Labels']:
            if 'values' in slots['Labels']:
                values = slots['Labels']['values']
                for v in values:
                    keywords.append(v['value']['interpretedValue'].lower())
    except:
        pass

    if not keywords:
        keywords = [query.lower()]
        #return {
        #    "statusCode": 200,
        #    "headers": {
        #        "Content-Type": "application/json",
        #        "Access-Control-Allow-Origin": "*"
        #        },
        #    "body": json.dumps({"results": []})
        #}

    print("keywords: ", keywords)

    # OpenSearch query

    should_clauses = []
    for k in keywords:
        should_clauses.append({
            "match": {
                "labels": {
                    "query": k,
                    "fuzziness": "AUTO"
                }
            }
        })

    query_body = {
        "query": {
            "bool": {
                "should": should_clauses
            }
        }
    }

    url = f"{host}/{index}/_search"
    payload = json.dumps(query_body).encode("utf-8")

    auth_str = f"{username}:{password}"
    encoded_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth}"
    }

    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST"
    )

    results = []

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))

            hits = res_body.get('hits', {}).get('hits', [])

            for hit in hits:
                results.append({
                    "url": f"https://{hit['_source']['bucket']}.s3.amazonaws.com/{hit['_source']['objectKey']}"
                })

    except Exception as e:
        print(f"OpenSearch Error: {e}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": '*'
        },
        "body": json.dumps({"results": results})
    }
