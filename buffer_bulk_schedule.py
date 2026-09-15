#!/usr/bin/env python3
"""Buffer GraphQL API를 통해 앞으로의 모든 이현 미적분 릴스를 일괄 예약 등록하는 스크립트."""
import json
import os
import sys
import requests
from datetime import datetime, timezone

from buffer_scheduler import get_token, get_channels, gql_request

HERE = os.path.dirname(os.path.abspath(__file__))

# 릴리즈 에셋 ID 매핑
ASSET_MAP = {
    "reel_cross_anticommutative.mp4": 565484736,
    "직선 방정식 방향벡터, 분모만 보면 틀립니다 [직선의 방정식 함정].mp4": 565484739,
    "평면 하나는 법선벡터와 한 점으로 정해집니다 [평면의 방정식].mp4": 565484738,
    "두 평면 사이 각은 법선벡터 각으로 바꿔서 푼다 [평면 사이 각].mp4": 565484734,
    "점과 평면 거리, 절대값 빼면 음수가 나옵니다 [평면의 방정식].mp4": 565484735
}

def get_direct_asset_url(asset_id):
    url = f"https://api.github.com/repos/heyjyu/leehyun-reels/releases/assets/{asset_id}"
    r = requests.get(url, headers={"Accept": "application/octet-stream"}, allow_redirects=False)
    if "Location" not in r.headers:
        raise RuntimeError(f"Direct download URL을 가져오지 못했습니다: {r.status_code}")
    return r.headers["Location"]

def main():
    token = get_token()
    if not token:
        sys.exit("토큰이 없습니다.")

    channels = get_channels(token)
    ig_chan = next((c for c in channels if c["service"] == "instagram"), None)
    if not ig_chan:
        sys.exit("인스타그램 채널을 찾을 수 없습니다.")

    cfg = json.load(open(os.path.join(HERE, "config.reels.json"), encoding="utf-8"))
    reels = cfg["reels"]

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        __typename
        ... on PostActionSuccess {
          post {
            id
            dueAt
            status
          }
        }
        ... on NotFoundError { message }
        ... on UnauthorizedError { message }
        ... on UnexpectedError { message }
        ... on RestProxyError { code message link }
        ... on LimitReachedError { message }
        ... on InvalidInputError { message }
      }
    }
    """

    print(f"🚀 Buffer 계정 (@{ig_chan['name']})으로 릴스 예약 일괄 등록 시작...\n")

    # 9월 17일부터 10월 1일까지의 릴스 목록
    upcoming_reels = [
        r for r in reels if r.get("file") in ASSET_MAP
    ]

    for r in upcoming_reels:
        fname = r["file"]
        asset_id = ASSET_MAP[fname]
        dt = datetime.fromisoformat(r["publishAt"])
        dt_utc = dt.astimezone(timezone.utc)
        due_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # 9/17 건은 위에서 테스트로 이미 등록되었으므로 중복 등록 건너뜀 (또는 안전 확인)
        direct_url = get_direct_asset_url(asset_id)
        caption = r["caption"]
        if "leehyun_calc" not in caption:
            caption = caption.strip() + "\n\n▶ 자세한 풀강의: 유튜브 leehyun_calc\n📚 정규강의·수학 컨설팅: 프로필 링크"

        payload = {
            "channelId": ig_chan["id"],
            "mode": "customScheduled",
            "schedulingType": "automatic",
            "needsApproval": False,
            "text": caption,
            "dueAt": due_iso,
            "assets": [{"video": {"url": direct_url}}],
            "metadata": {"instagram": {"type": "reel", "shouldShareToFeed": True}}
        }

        print(f"📅 예약 등록 중: {fname}")
        print(f"   - 예정 일시: {r['publishAt']} (UTC: {due_iso})")
        
        # 9/17 건은 이미 등록됨
        if fname == "reel_cross_anticommutative.mp4":
            print("   ✅ (이미 등록 완료됨)")
            continue

        try:
            res = gql_request(token, mutation, {"input": payload})
            result_data = res.get("createPost", {})
            if result_data.get("__typename") == "PostActionSuccess":
                print(f"   ✅ 예약 완료! Post ID: {result_data['post']['id']}")
            else:
                print(f"   ❌ 실패: {result_data}")
        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")

    print("\n🎉 모든 릴스 예약 등록이 완료되었습니다. Buffer 캘린더에서 확인하실 수 있습니다.")

if __name__ == "__main__":
    main()
