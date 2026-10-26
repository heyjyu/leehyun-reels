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
        "file": "reel_10_indep_var.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_10/reel_10_indep_var.mp4",
        "title": "독립변수의 진짜 의미는 이변수를 배워야 보인다 [이변수함수]",
        "publishAt": "2026-11-09T18:00:00+09:00",
        "caption": """독립변수의 진짜 의미는 이변수를 배워야 보인다 [이변수함수]

독립변수는 왜 '독립'변수일까? 1변수에서는 체감하기 어렵지만, 이변수함수에서 변수 2개를 내 맘대로 던져볼 때 비로소 그 진짜 의미가 보입니다!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #이변수함수 #독립변수 #대학수학"""
    },
    {
        "file": "reel_10_bell_shell.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_10/reel_10_bell_shell.mp4",
        "title": "이변수 그래프를 꽉 찬 종으로 알면 100% 틀립니다 [이변수함수 그래프]",
        "publishAt": "2026-11-12T18:00:00+09:00",
        "caption": """이변수 그래프를 꽉 찬 종으로 알면 100% 틀립니다 [이변수함수 그래프]

z = 4 - x² - y²의 그래프는 속이 꽉 찬 종 모양일까요? 껍데기 곡면일까요? 1초 만에 정리하는 공간 곡면의 직관!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #이변수함수 #공간곡면 #대학수학"""
    },
    {
        "file": "reel_10_triplane.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_10/reel_10_triplane.mp4",
        "title": "삼각형 하나로 무한한 평면을 그리는 법 3초 컷 [공간좌표 절편 스케치]",
        "publishAt": "2026-11-16T18:00:00+09:00",
        "caption": """삼각형 하나로 무한한 평면을 그리는 법 3초 컷 [공간좌표 절편 스케치]

공간에서 평면의 방정식 스케치할 때 평면을 다 그리려고 하면 멘붕 옵니다. x, y, z 절편 3개 찍고 삼각형만 그리면 스케치 끝!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #평면방정식 #절편스케치 #대학수학"""
    },
    {
        "file": "reel_10_pathtrap.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_10/reel_10_pathtrap.mp4",
        "title": "경로 두 개가 같아도 극한 있다고 하면 무조건 틀립니다 [이변수 극한]",
        "publishAt": "2026-11-19T18:00:00+09:00",
        "caption": """경로 두 개가 같아도 극한 있다고 하면 무조건 틀립니다 [이변수 극한]

두 경로에서 극한값이 0으로 같게 나왔다고 수렴한다고 쓰면 0점 감점! 무수히 많은 경로 중 단 하나라도 다르면 극한은 없습니다.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #이변수함수 #이변수극한 #대학수학"""
    },
    {
        "file": "reel_10_diag12.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_10/reel_10_diag12.mp4",
        "title": "x축·y축은 0인데 대각선은 1/2? 극한 비존재 증명 치트키 [이변수 극한]",
        "publishAt": "2026-11-23T18:00:00+09:00",
        "caption": """x축·y축은 0인데 대각선은 1/2? 극한 비존재 증명 치트키 [이변수 극한]

x축과 y축으로 접근하면 극한값이 0인데, y=x 대각선으로 가면 1/2이 되는 반전! 이변수 극한이 존재하지 않음을 단번에 보여주는 핵심 예제입니다.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #이변수함수 #이변수극한 #대학수학"""
    }
]

def main():
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
            "metadata": {"instagram": {"type": "reel", "shouldShareToFeed": True}}
        }

        pub_at = item["publishAt"]
        print(f"📅 Buffer 예약 등록 중: {item['title']}")
        print(f"   - 예정 일시: {pub_at} (UTC: {due_iso})")
        res = gql_request(token, create_mut, {"input": payload})
        result_data = res.get("createPost", {})
        if result_data.get("__typename") == "PostActionSuccess":
            pid = result_data["post"]["id"]
            print(f"   ✅ Buffer 예약 완료! Post ID: {pid}")
        else:
            print(f"   ❌ 실패: {result_data}")

    print("\n✨ 10강 릴스 5편 Buffer 예약 완료!")

if __name__ == "__main__":
    main()
