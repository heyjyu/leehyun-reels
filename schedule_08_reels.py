import json, os, requests
from datetime import datetime, timezone
from buffer_scheduler import get_token, get_channels, gql_request

token = get_token()
channels = get_channels(token)
ig_chan = next(c for c in channels if c["service"] == "instagram")

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
        "file": "reel_08_surface_vs_curve.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_08/reel_08_surface_vs_curve.mp4",
        "title": "원기둥 옆면을 곡선이라고 생각했다면 100% 오답 [공간곡선 vs 곡면]",
        "publishAt": "2026-10-05T18:00:00+09:00",
        "caption": """원기둥 옆면을 곡선이라고 생각했다면 100% 오답 [공간곡선 vs 곡면]

공간에서 파라미터가 1개면 곡선(1차원), 2개면 곡면(2차원)입니다. r(t)=(cos t, sin t, z)에서 z가 자유로우면 곡선이 아니라 원기둥 곡면 전체가 됩니다.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #공간도형 #공간곡선 #매개변수 #벡터함수 #대학수학"""
    },
    {
        "file": "reel_08_helix.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_08/reel_08_helix.mp4",
        "title": "원기둥 타고 올라가는 곡선의 정체? 헬릭스(나선) 1분 컷 [공간곡선]",
        "publishAt": "2026-10-08T18:00:00+09:00",
        "caption": """원기둥 타고 올라가는 곡선의 정체? 헬릭스(나선) 1분 컷 [공간곡선]

(cos t, sin t, t)의 정체! 밑면에서는 원을 그리며 회전하고, z축으로는 시간에 비례해 일정하게 상승하는 대표적 공간곡선 헬릭스(Helix, 원나선)입니다.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #공간곡선 #헬릭스 #나선 #벡터함수 #대학수학"""
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
