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
        "title": "극한 계산 노가다 금지! y를 숫자로 보면 3초 만에 끝납니다 [편미분 치트키]",
        "publishAt": "2026-11-26T18:00:00+09:00",
        "caption": """극한 계산 노가다 금지! y를 숫자로 보면 3초 만에 끝납니다 [편미분 치트키]

평균변화율 극한 계산 노가다 그만! y를 숫자로 취급하고 미분하면 3초 만에 끝나는 편미분 실전 치트키 대공개!

▶ 전체 강의: 유튜브 leehyun_calc
📚 정규강의·전자책: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #편미분 #대학수학 #이현미적분"""
    },
    {
        "file": "reel_11_tplane_hs.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_11/reel_11_tplane_hs.mp4",
        "title": "접평면 공식 쌩으로 외우지 마세요, 고등수학 공식에 딱 하나만 더하면 3초 컷 [접평면 치트키]",
        "publishAt": "2026-11-30T18:00:00+09:00",
        "caption": """접평면 공식 쌩으로 외우지 마세요, 고등수학 공식에 딱 하나만 더하면 3초 컷 [접평면 치트키]

접평면 방정식 쌩으로 외우느라 멘붕 오셨나요? 고등수학에서 배운 접선 공식에 z항 하나만 더하면 3초 만에 끝납니다!

▶ 전체 강의: 유튜브 leehyun_calc
📚 정규강의·전자책: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #접평면 #대학수학 #이현미적분"""
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
                        "metadata": {
                            "thumbnailOffset": 3000
                        }
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
