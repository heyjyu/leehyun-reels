#!/usr/bin/env python3
"""Instagram 캐러셀(이미지 여러 장) 자동 발행 — Instagram Graph API · Content Publishing.

reels_upload.py 와 평행. config.carousel.json 의 posts 를 발행한다.
릴스는 파일 바이트 업로드(resumable)지만 **캐러셀 이미지는 공개 URL(image_url) 필수** →
이미지는 heyjyu/leehyun-ig-assets(공개 repo)의 raw URL 사용.

흐름: ① 자식 이미지 컨테이너 N개 → ② CAROUSEL 컨테이너(children) → ③ media_publish.
Graph API는 즉시 게시(예약 없음) → "예약"은 cron: 매일 그 시각 --due 실행, publishAt 도래분만 발행.

사용:
  python3 carousel_upload.py --due       # publishAt<=now 미발행(cron용)
  python3 carousel_upload.py --now       # 미발행 전부 지금
  python3 carousel_upload.py --key lead3 # 특정 key 지금
  python3 carousel_upload.py --list      # 상태만(발행 안 함)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
API = "v21.0"
GRAPH = f"https://graph.facebook.com/{API}"
STATE_FILE = "published_carousel.json"


def load_json(name, default=None):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save_state(state):
    json.dump(state, open(os.path.join(HERE, STATE_FILE), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def create_child(ig_user_id, token, image_url):
    """단일 이미지 자식 컨테이너 생성. id 반환."""
    r = requests.post(f"{GRAPH}/{ig_user_id}/media", data={
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": token,
    }, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def wait_finished(cid, token, tries=30, delay=6):
    """컨테이너가 FINISHED 될 때까지 폴링."""
    for _ in range(tries):
        s = requests.get(f"{GRAPH}/{cid}",
                         params={"fields": "status_code,status", "access_token": token},
                         timeout=30).json()
        code = s.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"컨테이너 처리 실패: {s}")
        time.sleep(delay)
    raise RuntimeError("컨테이너 처리 타임아웃")


def publish_carousel(ig_user_id, token, image_urls, caption):
    """자식 이미지 컨테이너 → CAROUSEL 컨테이너 → 발행. media id 반환."""
    if not (2 <= len(image_urls) <= 10):
        raise RuntimeError(f"캐러셀은 이미지 2~10장이어야 함(현재 {len(image_urls)}장)")
    # 1) 자식 이미지 컨테이너
    children = []
    for i, url in enumerate(image_urls, 1):
        cid = create_child(ig_user_id, token, url)
        print(f"    자식 {i}/{len(image_urls)}: {cid}")
        children.append(cid)
    # 2) CAROUSEL 컨테이너
    r = requests.post(f"{GRAPH}/{ig_user_id}/media", data={
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    }, timeout=60)
    r.raise_for_status()
    parent = r.json()["id"]
    print(f"    캐러셀 컨테이너: {parent}  처리 대기…")
    wait_finished(parent, token)
    # 3) 발행
    r = requests.post(f"{GRAPH}/{ig_user_id}/media_publish",
                      data={"creation_id": parent, "access_token": token}, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def resolve_images(cfg, post):
    base = (cfg.get("image_base") or "").rstrip("/")
    out = []
    for img in post["images"]:
        out.append(img if img.startswith("http") else f"{base}/{img}")
    return out


def due(post, now):
    pa = post.get("publishAt")
    return True if not pa else datetime.fromisoformat(pa) <= now


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--due", action="store_true", help="publishAt<=now 미발행(cron용)")
    g.add_argument("--now", action="store_true", help="미발행 전부 지금")
    g.add_argument("--key", help="특정 key만 지금")
    g.add_argument("--list", action="store_true", help="상태만")
    args = ap.parse_args()

    cfg = load_json("config.carousel.json")
    if not cfg:
        sys.exit("config.carousel.json 없음.")
    state = load_json(STATE_FILE, {}) or {}
    posts = cfg["posts"]

    if args.list:
        for p in posts:
            st = "발행됨" if p["key"] in state else ("skip" if p.get("skip") else p.get("publishAt", "now"))
            print(f"  {st:26}  {p['key']}  ({len(p['images'])}장)")
        return

    # 토큰 로딩 (reels_upload.py 와 동일 규약: token.json 없으면 env IG_TOKEN/IG_USER_ID)
    tok = load_json("token.json")
    if not tok:
        if os.environ.get("IG_TOKEN"):
            tok = {"access_token": os.environ["IG_TOKEN"],
                   "ig_user_id": os.environ.get("IG_USER_ID") or "",
                   "ig_username": os.environ.get("IG_USERNAME", "leehyun_calc")}
        else:
            sys.exit("token.json/IG_TOKEN 없음 — GitHub Secrets 설정 확인")
    if not tok.get("ig_user_id"):
        try:
            r = requests.get(f"{GRAPH}/me/accounts",
                             params={"fields": "instagram_business_account", "access_token": tok["access_token"]},
                             timeout=30).json()
            for pg in r.get("data", []):
                iba = pg.get("instagram_business_account")
                if iba:
                    tok["ig_user_id"] = iba["id"]; break
        except Exception as e:
            print("ig_user_id 자동탐색 실패:", e)
    if not tok.get("ig_user_id"):
        sys.exit("ig_user_id 를 찾지 못했습니다 (IG_USER_ID 설정 또는 권한 확인).")

    now = datetime.now(timezone.utc).astimezone()

    todo = []
    for p in posts:
        if p.get("skip") or p["key"] in state:
            continue
        if args.key:
            if p.get("key") == args.key:
                todo.append(p)
        elif args.now:
            todo.append(p)
        elif due(p, now):
            todo.append(p)
    if not todo:
        print("발행할 캐러셀 없음.")
        return

    ig, token = tok["ig_user_id"], tok["access_token"]
    print(f"발행 대상 {len(todo)}개 (@{tok.get('ig_username','?')})")
    for p in todo:
        urls = resolve_images(cfg, p)
        print(f"⬆️  {p['key']}  ({len(urls)}장)")
        try:
            mid = publish_carousel(ig, token, urls, p.get("caption", ""))
            state[p["key"]] = {"mediaId": mid, "at": now.isoformat()}
            save_state(state)
            print(f"    ✅ 발행 완료 mediaId: {mid}")
        except requests.HTTPError as e:
            print(f"    ❌ 실패: {e.response.text[:300]}")
        except Exception as e:
            print(f"    ❌ 실패: {e}")
    print(f"끝. 상태는 {STATE_FILE} 참고.")


if __name__ == "__main__":
    main()
