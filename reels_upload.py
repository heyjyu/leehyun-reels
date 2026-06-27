#!/usr/bin/env python3
"""Instagram 릴스 자동 발행 (Instagram Graph API · Content Publishing).

유튜브 업로더와 평행. plan.json → config.reels.json(produce.py가 생성)의 릴스를 발행.
**resumable 업로드**(파일 바이트 직접 전송)라 공개 URL·터널 불필요. Graph API는 즉시 게시
(예약 없음) → "예약"은 cron으로: 그 시각에 `--due`를 돌리면 publishAt이 오늘인 릴스 발행.

사전: token.json (get_ig_token.py 로 생성: access_token=페이지토큰, ig_user_id)
사용:
  python3 reels_upload.py --due          # publishAt<=now 미발행 릴스(cron용)
  python3 reels_upload.py --key area      # 특정 릴스 지금
  python3 reels_upload.py --now           # 미발행 전부 지금
  python3 reels_upload.py --list          # 상태만(발행 안 함)
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
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{API}"


def load_json(name, default=None):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save_state(state):
    json.dump(state, open(os.path.join(HERE, "published.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def publish_reel(ig_user_id, token, file_path, caption):
    """resumable: ① 컨테이너 생성 ② 파일 바이트 업로드 ③ 처리 폴링 ④ 발행. media id 반환."""
    size = os.path.getsize(file_path)
    # 1) 컨테이너(REELS, resumable)
    r = requests.post(f"{GRAPH}/{ig_user_id}/media", data={
        "media_type": "REELS", "upload_type": "resumable",
        "caption": caption, "access_token": token,
    }, timeout=60)
    r.raise_for_status()
    cid = r.json()["id"]
    print(f"    컨테이너: {cid}  (업로드 {size/1e6:.1f}MB)")
    # 2) 파일 바이트 업로드(rupload)
    with open(file_path, "rb") as f:
        up = requests.post(f"{RUPLOAD}/{cid}", headers={
            "Authorization": f"OAuth {token}",
            "offset": "0", "file_size": str(size),
        }, data=f, timeout=600)
    up.raise_for_status()
    if not up.json().get("success", True):
        raise RuntimeError(f"업로드 실패: {up.text}")
    print("    업로드 완료, 처리 대기…")
    # 3) 처리 상태 폴링
    for _ in range(40):                       # 최대 ~6.5분
        time.sleep(10)
        s = requests.get(f"{GRAPH}/{cid}",
                         params={"fields": "status_code,status", "access_token": token},
                         timeout=30).json()
        code = s.get("status_code")
        print(f"    처리중… {code}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"처리 실패: {s}")
    else:
        raise RuntimeError("처리 타임아웃")
    # 4) 발행
    r = requests.post(f"{GRAPH}/{ig_user_id}/media_publish",
                      data={"creation_id": cid, "access_token": token}, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def due(reel, now):
    pa = reel.get("publishAt")
    return True if not pa else datetime.fromisoformat(pa) <= now


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--due", action="store_true", help="publishAt<=now 미발행(cron용)")
    g.add_argument("--now", action="store_true", help="미발행 전부 지금")
    g.add_argument("--key", help="특정 키만 지금")
    g.add_argument("--list", action="store_true", help="상태만")
    args = ap.parse_args()

    cfg = load_json("config.reels.json")
    if not cfg:
        sys.exit("config.reels.json 없음 — produce.py ... --upload-reels 로 생성.")
    state = load_json("published.json", {}) or {}
    reels = cfg["reels"]

    if args.list:
        for r in reels:
            st = "발행됨" if r["file"] in state else ("skip" if r.get("skip") else r.get("publishAt", "now"))
            print(f"  {st:26}  {r['file']}")
        return

    tok = load_json("token.json")
    if not tok:  # GitHub Actions 등: 파일 없으면 환경변수(IG_TOKEN/IG_USER_ID)에서
        import os as _os
        if _os.environ.get("IG_TOKEN") and _os.environ.get("IG_USER_ID"):
            tok = {"access_token": _os.environ["IG_TOKEN"], "ig_user_id": _os.environ["IG_USER_ID"],
                   "ig_username": _os.environ.get("IG_USERNAME", "leehyun_calc")}
        else:
            sys.exit("token.json/IG_TOKEN 없음 — get_ig_token.py 또는 GitHub Secrets 설정")
    now = datetime.now(timezone.utc).astimezone()

    todo = []
    for r in reels:
        if r.get("skip") or r["file"] in state:
            continue
        if args.key:
            if r.get("key") == args.key:
                todo.append(r)
        elif args.now:
            todo.append(r)
        elif due(r, now):                     # --due(기본)
            todo.append(r)
    if not todo:
        print("발행할 릴스 없음.")
        return

    ig, token, vdir = tok["ig_user_id"], tok["access_token"], cfg["video_dir"]
    print(f"발행 대상 {len(todo)}개 (@{tok.get('ig_username','?')})")
    for r in todo:
        path = os.path.join(vdir, r["file"])
        if not os.path.exists(path):
            print(f"⚠️  파일 없음, 건너뜀: {r['file']}")
            continue
        print(f"⬆️  {r['file']}")
        try:
            mid = publish_reel(ig, token, path, r.get("caption", ""))
            state[r["file"]] = {"mediaId": mid, "at": now.isoformat()}
            save_state(state)
            print(f"    ✅ 발행 완료 mediaId: {mid}")
        except requests.HTTPError as e:
            print(f"    ❌ 실패: {e.response.text[:300]}")
        except Exception as e:
            print(f"    ❌ 실패: {e}")
    print("끝. 상태는 published.json 참고.")


if __name__ == "__main__":
    main()
