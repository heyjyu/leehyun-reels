#!/usr/bin/env python3
"""Buffer GraphQL API를 통한 이현 미적분 인스타그램 릴스 자동 예약 발행 스크립트."""
import json
import os
import sys
import requests
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUFFER_API = "https://api.buffer.com"
RAW_GITHUB_BASE = "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/videos"

def get_token():
    tok_file = os.path.join(HERE, "buffer_token.txt")
    if os.path.exists(tok_file):
        with open(tok_file, "r", encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t
    return os.environ.get("BUFFER_ACCESS_TOKEN", "")

def gql_request(token, query, variables=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    r = requests.post(BUFFER_API, headers=headers, json={"query": query, "variables": variables or {}}, timeout=30)
    r.raise_for_status()
    res = r.json()
    if "errors" in res:
        raise RuntimeError(f"GraphQL Error: {res['errors']}")
    return res.get("data", {})

def get_channels(token):
    acc = gql_request(token, "query { account { organizations { id name } } }")
    orgs = acc["account"]["organizations"]
    if not orgs:
        raise RuntimeError("조직(Organization)을 찾을 수 없습니다.")
    org_id = orgs[0]["id"]
    
    q = """
    query GetChannels($input: ChannelsInput!) {
      channels(input: $input) {
        id
        name
        service
        serviceId
        type
      }
    }
    """
    data = gql_request(token, q, {"input": {"organizationId": org_id}})
    return data.get("channels", [])

def schedule_reel(token, channel_id, text, video_url, due_iso, share_now=False):
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            dueAt
            status
          }
        }
      }
    }
    """
    mode = "shareNow" if share_now else "customScheduled"
    scheduling_type = "automatic"
    
    payload = {
        "channelId": channel_id,
        "mode": mode,
        "schedulingType": scheduling_type,
        "needsApproval": False,
        "text": text,
        "assets": [
            {
                "video": {
                    "url": video_url
                }
            }
        ],
        "metadata": {
            "instagram": {
                "type": "reel",
                "shouldShareToFeed": True
            }
        }
    }
    if not share_now:
        payload["dueAt"] = due_iso
        
    return gql_request(token, mutation, {"input": payload})

def main():
    token = get_token()
    if not token:
        sys.exit("buffer_token.txt 또는 BUFFER_ACCESS_TOKEN 환경변수 필요.")
        
    channels = get_channels(token)
    ig_chan = next((c for c in channels if c["service"] == "instagram"), None)
    if not ig_chan:
        sys.exit(f"연결된 인스타그램 채널이 없습니다. (발견된 채널: {[c['name'] for c in channels]})")
        
    print(f"✅ Buffer 인스타그램 채널 연결 확인: @{ig_chan['name']} (ID: {ig_chan['id']})")
    return ig_chan

if __name__ == "__main__":
    main()
