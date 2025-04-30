import json
import os
import re
import requests

FASTAPI_URL = os.environ.get("FASTAPI_URL")

def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

def lambda_handler(event):
    try:
        print("Received event:", json.dumps(event))

        # 認証情報の取得（必要に応じて使う）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # プロンプト形式に整形（直近の履歴＋現在のメッセージ）
        full_prompt = ""
        for msg in conversation_history:
            full_prompt += f"{msg['role']}: {msg['content']}\n"
        full_prompt += f"user: {message}\nassistant:"

        # FastAPIに対してリクエスト送信
        response = requests.post(
            FASTAPI_URL,
            json={
                "prompt": full_prompt,
                "max_new_tokens": 512,
                "temperature": 0.0,
                "top_p": 0.9,
                "do_sample": False
            },
            timeout=300
        )

        response.raise_for_status()
        response_data = response.json()

        assistant_response = response_data.get("generated_text", "応答が生成されませんでした。")

        # 会話履歴に追加
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": assistant_response})

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
