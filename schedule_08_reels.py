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
        "file": "reel_08_component_diff.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_08/reel_08_component_diff.mp4",
        "title": "성분별 미분은 벡터함수 미분의 정의가 아닙니다 [공간곡선]",
        "publishAt": "2026-10-12T18:00:00+09:00",
        "caption": """성분별 미분은 벡터함수 미분의 정의가 아닙니다 [공간곡선]

벡터함수의 도함수는 각 성분을 미분하는 게 아니라, 두 점을 잇는 할선벡터의 극한으로 정의됩니다. 왜 성분별 미분이 가능한지 그 숨겨진 원리를 1분 만에 확인하세요!

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #공간곡선 #벡터함수 #대학수학"""
    },
    {
        "file": "reel_08_tangent_vector.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_08/reel_08_tangent_vector.mp4",
        "title": "접선벡터 크기가 무한대라고 답하면 바로 틀립니다 [벡터함수 미분]",
        "publishAt": "2026-10-15T18:00:00+09:00",
        "caption": """접선벡터 크기가 무한대라고 답하면 바로 틀립니다 [벡터함수 미분]

미분계수가 존재하려면 크기가 유한하고 0이 아니어야 합니다. 매끄러운 곡선에서 접선벡터의 크기와 단위접선벡터 T(t)를 구할 때 가장 많이 하는 실수를 짚어드립니다.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #접선벡터 #단위접선벡터 #대학수학"""
    },
    {
        "file": "reel_08_sphere_orthogonal.mp4",
        "url": "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/compressed_08/reel_08_sphere_orthogonal.mp4",
        "title": "구 표면을 어떻게 기어가도 속도는 반지름과 수직인 이유 [벡터함수 공간곡선]",
        "publishAt": "2026-10-19T18:00:00+09:00",
        "caption": """구 표면을 어떻게 기어가도 속도는 반지름과 수직인 이유 [벡터함수 공간곡선]

구 표면 위를 아무리 불규칙하게 움직여도 속도벡터는 항상 위치벡터와 직교합니다! 벡터 내적의 미분법으로 10초 만에 끝내는 필수 증명 치트키.

▶ 자세한 풀강의: 유튜브 leehyun_calc
📚 정규강의·수학 컨설팅: 프로필 링크

메가스터디 대학인강 유니스터디 · 이현 교수님
#릴스 #미적분 #공간곡선 #벡터내적 #대학수학"""
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
