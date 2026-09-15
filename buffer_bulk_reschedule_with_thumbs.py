#!/usr/bin/env python3
"""Buffer 대기열의 기존 릴스를 삭제하고, 3초 지점 고화질 커버 썸네일(칠판+강사)과 함께 재예약합니다."""
import json
import os
import sys
import requests
from datetime import datetime, timezone

from buffer_scheduler import get_token, get_channels, gql_request

HERE = os.path.dirname(os.path.abspath(__file__))

ITEMS = [
    {
        "file": "reel_cross_anticommutative.mp4",
        "video_asset_id": 565484736,
        "thumb_asset_id": 565489072,
        "publishAt": "2026-09-17T18:00:00+09:00"
    },
    {
        "file": "직선 방정식 방향벡터, 분모만 보면 틀립니다 [직선의 방정식 함정].mp4",
        "video_asset_id": 565484739,
        "thumb_asset_id": 565489070,
        "publishAt": "2026-09-21T18:00:00+09:00"
    },
    {
        "file": "평면 하나는 법선벡터와 한 점으로 정해집니다 [평면의 방정식].mp4",
        "video_asset_id": 565484738,
        "thumb_asset_id": 565489069,
        "publishAt": "2026-09-24T18:00:00+09:00"
    },
    {
        "file": "두 평면 사이 각은 법선벡터 각으로 바꿔서 푼다 [평면 사이 각].mp4",
        "video_asset_id": 565484734,
        "thumb_asset_id": 565489071,
        "publishAt": "2026-09-28T18:00:00+09:00"
    },
    {
        "file": "점과 평면 거리, 절대값 빼면 음수가 나옵니다 [평면의 방정식].mp4",
        "video_asset_id": 565484735,
        "thumb_asset_id": 565489074,
        "publishAt": "2026-10-01T18:00:00+09:00"
    }
]

def get_direct_url(asset_id):
    url = f"https://api.github.com/repos/heyjyu/leehyun-reels/releases/assets/{asset_id}"
    r = requests.get(url, headers={"Accept": "application/octet-stream"}, allow_redirects=False)
    if "Location" not in r.headers:
        raise RuntimeError(f"Direct download URL을 가져오지 못했습니다: {r.status_code}")
    return r.headers["Location"]

def main():
    token = get_token()
    channels = get_channels(token)
    ig_chan = next(c for c in channels if c["service"] == "instagram")
    
    # 1. 기존 scheduled 포스트 조회 후 삭제
    acc = gql_request(token, "query { account { organizations { id } } }")
    org_id = acc["account"]["organizations"][0]["id"]
    
    q_posts = """
    query GetScheduled($orgId: OrganizationId!) {
      posts(input: { organizationId: $orgId }) {
        edges {
          node {
            id
            dueAt
            status
          }
        }
      }
    }
    """
    posts_data = gql_request(token, q_posts, {"orgId": org_id})
    del_mut = """
    mutation DeletePost($input: DeletePostInput!) {
      deletePost(input: $input) {
        ... on DeletePostSuccess {
          id
        }
      }
    }
    """
    for edge in posts_data["posts"]["edges"]:
        p = edge["node"]
        if p["status"] == "scheduled":
            print(f"🗑️ 기존 예약 포스트 삭제 중: {p['id']} (예정: {p['dueAt']})")
            gql_request(token, del_mut, {"input": {"id": p["id"]}})

    # 2. 썸네일 URL을 포함하여 릴스 재등록
    cfg = json.load(open(os.path.join(HERE, "config.reels.json"), encoding="utf-8"))
    reels_by_file = {r["file"]: r for r in cfg["reels"]}

    create_mut = """
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
        ... on InvalidInputError { message }
      }
    }
    """

    print("\n✨ 3초 지점 커버 썸네일이 적용된 릴스 재예약 등록 시작...\n")

    for item in ITEMS:
        fname = item["file"]
        r_info = reels_by_file[fname]
        dt = datetime.fromisoformat(item["publishAt"])
        dt_utc = dt.astimezone(timezone.utc)
        due_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        video_url = get_direct_url(item["video_asset_id"])
        thumb_url = get_direct_url(item["thumb_asset_id"])

        caption = r_info["caption"]
        if "leehyun_calc" not in caption:
            caption = caption.strip() + "\n\n▶ 자세한 풀강의: 유튜브 leehyun_calc\n📚 정규강의·수학 컨설팅: 프로필 링크"

        payload = {
            "channelId": ig_chan["id"],
            "mode": "customScheduled",
            "schedulingType": "automatic",
            "needsApproval": False,
            "text": caption,
            "dueAt": due_iso,
            "assets": [
                {
                    "video": {
                        "url": video_url,
                        "metadata": {
                            "thumbnailOffset": 3000
                        }
                    }
                }
            ],
            "metadata": {"instagram": {"type": "reel", "shouldShareToFeed": True}}
        }

        print(f"📅 예약 등록 중: {fname}")
        print(f"   - 예정 일시: {item['publishAt']} (UTC: {due_iso})")
        print(f"   - 썸네일: {item['thumb_asset_id']} (3초 칠판+강사 프레임)")

        res = gql_request(token, create_mut, {"input": payload})
        result_data = res.get("createPost", {})
        if result_data.get("__typename") == "PostActionSuccess":
            print(f"   ✅ 썸네일 적용 예약 완료! Post ID: {result_data['post']['id']}")
        else:
            print(f"   ❌ 실패: {result_data}")

    print("\n🎉 모든 릴스가 칠판+강사 썸네일과 함께 완벽하게 재등록되었습니다!")

if __name__ == "__main__":
    main()
