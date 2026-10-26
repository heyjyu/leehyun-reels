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
        "file": "reel_09_arclen_speed.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_09/reel_09_arclen_speed.mp4",
        "title": "곡선의 길이 공식, 사실 속력을 적분한 것에 불과합니다 [호의 길이]",
        "publishAt": "2026-10-22T18:00:00+09:00",
        "caption": """곡선의 길이 공식, 사실 속력을 적분한 것에 불과합니다 [호의 길이]

복잡해 보이는 공간곡선의 길이 공식, 사실 위치벡터를 미분한 접선벡터(속력)의 크기를 시간에 대해 적분한 물리적 직관과 완벽히 같습니다!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #호의길이 #곡선의길이 #대학수학"""
    },
    {
        "file": "reel_09_curv_clock.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_09/reel_09_curv_clock.mp4",
        "title": "단위접선벡터가 시계처럼 꺾이는 곳, 거기가 곡률 최대 [곡률 개념]",
        "publishAt": "2026-10-26T18:00:00+09:00",
        "caption": """단위접선벡터가 시계처럼 꺾이는 곳, 거기가 곡률 최대 [곡률 개념]

곡률(Curvature)이란 이동한 거리에 대해 단위접선벡터 T(t)가 얼마나 급격하게 회전하는가를 나타내는 척도입니다. 시침처럼 팍팍 꺾일수록 곡률은 폭발합니다!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #곡률 #단위접선벡터 #대학수학"""
    },
    {
        "file": "reel_09_curv_z0.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_09/reel_09_curv_z0.mp4",
        "title": "평면곡선 곡률을 2차원 벡터로 풀면 100% 막힙니다 [곡률 계산]",
        "publishAt": "2026-10-29T18:00:00+09:00",
        "caption": """평면곡선 곡률을 2차원 벡터로 풀면 100% 막힙니다 [곡률 계산]

y=f(x) 평면곡선의 곡률을 구할 때 z성분을 0으로 두고 3차원 외적 공식으로 밀어붙이면 단 10초 만에 끝납니다. 시험장 멘붕 방지 필수 치트키!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #곡률계산 #외적공식 #대학수학"""
    },
    {
        "file": "reel_09_norm_derive.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_09/reel_09_norm_derive.mp4",
        "title": "주단위법선벡터 N(t), 미분하고 크기 안 나누면 0점 감점 [주단위법선벡터]",
        "publishAt": "2026-11-02T18:00:00+09:00",
        "caption": """주단위법선벡터 N(t), 미분하고 크기 안 나누면 0점 감점 [주단위법선벡터]

단위접선벡터 T(t)를 미분한 벡터 T'(t)는 '단위'벡터가 아닙니다. 반드시 그 크기로 나누어 주어야 주단위법선벡터 N(t)가 완성됩니다. 서술형 단골 함정 대비!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #주단위법선 #단위접선벡터 #대학수학"""
    },
    {
        "file": "reel_09_binorm_cross.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_09/reel_09_binorm_cross.mp4",
        "title": "종법선벡터 B(t), 공식 복잡하게 외우지 마세요 [종법선벡터]",
        "publishAt": "2026-11-05T18:00:00+09:00",
        "caption": """종법선벡터 B(t), 공식 복잡하게 외우지 마세요 [종법선벡터]

공간곡선의 삼면체를 완성하는 마지막 축! 오른손 법칙에 의해 B(t) = T(t) x N(t) 외적 하나면 복잡한 공식 필요 없이 계산이 끝납니다.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #종법선벡터 #외적 #대학수학"""
    }
]

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

print("\n✨ Buffer 예약 완료!")
