#!/usr/bin/env python3
import json, os, requests
from datetime import datetime, timezone
from buffer_scheduler import get_token, get_channels, gql_request

token = get_token()
channels = get_channels(token)
ig_chan = next(c for c in channels if c.get("name") == "leehyun_calc" and c.get("service") == "instagram")

create_mut = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess {
      post {
        id
        dueAt
        status
        assets {
          __typename
          ... on VideoAsset {
            source
            thumbnail
            video {
              durationMs
              thumbnailOffset
              isVideoProcessing
            }
          }
        }
      }
    }
    ... on InvalidInputError { message }
  }
}
"""

TARGETS = [
    {
        "file": "reel_11_fx_number.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_11/reel_11_fx_number.mp4",
        "title": "변수 2개인데 y를 숫자로 본다고요? 편미분할 때 100% 감점당하는 착각 [편미분 정의]",
        "publishAt": "2026-11-26T18:00:00+09:00",
        "caption": """변수 2개인데 y를 숫자로 본다고요? 편미분할 때 100% 감점당하는 착각 [편미분 정의]

변수가 2개인데 y를 숫자로 취급해도 되는 진짜 수학적 이유는? 극한 계산 노가다 없이 편미분의 본질을 꿰뚫는 1분 특강!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #편미분 #편도함수 #대학수학"""
    },
    {
        "file": "reel_11_slice.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_11/reel_11_slice.mp4",
        "title": "3차원 곡면을 칼로 싹둑 잘랐더니 2차원 접선이 나온다? [편미분의 기하학]",
        "publishAt": "2026-11-30T18:00:00+09:00",
        "caption": """3차원 곡면을 칼로 싹둑 잘랐더니 2차원 접선이 나온다? [편미분의 기하학]

3차원 곡면 z=f(x,y)를 평면으로 싹둑 잘라내는 순간 나타나는 마법 같은 2차원 접선! 편미분의 기하학적 직관을 칠판으로 확인하세요.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #편미분 #미분기하 #대학수학"""
    },
    {
        "file": "reel_11_tplane_hs.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_11/reel_11_tplane_hs.mp4",
        "title": "접평면 공식 외우다 시험 망칩니다, 고1 공식에 딱 하나만 더하세요 [접평면 3초 컷]",
        "publishAt": "2026-12-03T18:00:00+09:00",
        "caption": """접평면 공식 외우다 시험 망칩니다, 고1 공식에 딱 하나만 더하세요 [접평면 3초 컷]

접평면 방정식 외우느라 멘붕 오셨나요? 고1 때 배운 접선 공식에 z항 하나만 더하면 3초 만에 끝납니다!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #접평면 #접선공식 #대학수학"""
    }
]

def main():
    print(f"=== Buffer 인스타그램 릴스 11강 예약 등록 (채널: {ig_chan['name']}) ===")
    for item in TARGETS:
        dt = datetime.fromisoformat(item["publishAt"])
        dt_utc = dt.astimezone(timezone.utc)
        due_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        payload = {
            "channelId": ig_chan["id"],
            "mode": "customScheduled",
            "schedulingType": "automatic",
            "needsApproval": False,
            "text": item["caption"],
            "dueAt": due_iso,
            "assets": [
                {
                    "video": {
                        "url": item["url"],
                        "thumbnailOffset": 3000
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

        print(f"등록 중: {item['file']} ({item['publishAt']}) -> {item['title'][:30]}...")
        res = gql_request(token, create_mut, {"input": payload})
        post_data = res.get("createPost", {})
        if "post" in post_data:
            p = post_data["post"]
            print(f"  [성공] ID: {p.get('id')} | 상태: {p.get('status')} | 예정: {p.get('dueAt')}")
        else:
            print(f"  [실패] {post_data}")

if __name__ == "__main__":
    main()
