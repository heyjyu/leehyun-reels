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
API = "v23.0"
GRAPH = f"https://graph.facebook.com/{API}"
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{API}"


def load_json(name, default=None):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save_state(state):
    json.dump(state, open(os.path.join(HERE, "published.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def _dump_resp(tag, resp):
    """진단용: 상태코드·fbtrace 헤더·본문 전체 출력."""
    hdr = {k: v for k, v in resp.headers.items()
           if k.lower() in ("x-fb-trace-id", "x-fb-rev", "x-fb-debug", "www-authenticate",
                            "facebook-api-version", "content-type")}
    print(f"    [{tag}] HTTP {resp.status_code} {hdr}")
    print(f"    [{tag}] body: {resp.text[:500]}")


def upload_container(ig_user_id, token, file_path, caption, verbose=False):
    """① 컨테이너 생성 ② 바이트 업로드 ③ 처리 폴링(FINISHED까지). 컨테이너 id 반환. 발행 안 함."""
    size = os.path.getsize(file_path)
    # 1) 컨테이너(REELS, resumable)
    r = requests.post(f"{GRAPH}/{ig_user_id}/media", data={
        "media_type": "REELS", "upload_type": "resumable",
        "caption": caption, "access_token": token,
    }, timeout=60)
    if verbose:
        _dump_resp("container", r)
    r.raise_for_status()
    cid = r.json()["id"]
    # ★ 컨테이너 응답의 uri를 그대로 사용(정본). 자체 조립 URL(v21/v23)은 Meta 버전업그레이드
    #   (v25.0, 2026-07 관측)에서 rupload가 400 ProcessingFailedError를 뱉으며 전부 막혔음.
    upload_uri = r.json().get("uri") or f"{RUPLOAD}/{cid}"
    print(f"    컨테이너: {cid}  (업로드 {size/1e6:.1f}MB → {upload_uri})")
    # 2) 파일 바이트 업로드(rupload) — 메모리로 읽어 Content-Length 확정 + octet-stream 명시
    data = open(file_path, "rb").read()
    up = requests.post(upload_uri, headers={
        "Authorization": f"OAuth {token}",
        "offset": "0", "file_size": str(size),
        "Content-Type": "application/octet-stream",
    }, data=data, timeout=600)
    if verbose or not up.ok:
        _dump_resp("rupload", up)
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
        print(f"    처리중… {code}  {s.get('status','')}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"처리 실패: {s}")
    else:
        raise RuntimeError("처리 타임아웃")
    return cid


def publish_reel(ig_user_id, token, file_path, caption):
    """업로드(컨테이너 FINISHED까지) 후 ④ 발행. media id 반환."""
    cid = upload_container(ig_user_id, token, file_path, caption)
    r = requests.post(f"{GRAPH}/{ig_user_id}/media_publish",
                      data={"creation_id": cid, "access_token": token}, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


# 릴스 CTA 댓글 — IG는 댓글·캡션 링크가 클릭 안 되므로 유튜브 채널명을 각인 + 프로필 링크 유도.
IG_CTA_COMMENT = (
    "풀강의 👉 유튜브 leehyun_calc\n"
    "▶ 자세한 강의: 유튜브에서 leehyun_calc 검색\n"
    "📚 정규강의·수학 컨설팅: 프로필 링크"
)


def post_comment(media_id, token, text=IG_CTA_COMMENT):
    """발행된 릴스에 CTA 댓글을 단다. instagram_manage_comments 권한 필요.
       권한이 없으면 예외 → 호출부에서 잡아 '발행 자체'는 성공으로 유지."""
    r = requests.post(f"{GRAPH}/{media_id}/comments",
                      data={"message": text, "access_token": token}, timeout=60)
    r.raise_for_status()
    return r.json().get("id")


# ★ 캡션 CTA(자동 삽입) — IG는 링크가 클릭 안 되므로 댓글이든 캡션이든 효과 동일한데,
#   캡션은 권한 없이 100% 자동이라 이쪽을 정본으로 씀(댓글은 권한 생기면 보너스).
#   해시태그 앞(본문 끝)에 삽입해 첫 화면 '더 보기' 근처에서 읽히게 함.
IG_CTA_CAPTION = (
    "▶ 자세한 풀강의: 유튜브 leehyun_calc\n"
    "📚 정규강의·수학 컨설팅: 프로필 링크"
)


def with_cta(caption, cta=IG_CTA_CAPTION):
    """캡션에 CTA를 자동 삽입. 이미 들어 있으면 그대로 둠(중복 방지).
       해시태그 블록이 있으면 그 '앞'에, 없으면 맨 끝에 붙인다."""
    if not caption:
        return cta
    if "leehyun_calc" in caption:          # 이미 CTA 있음
        return caption
    lines = caption.rstrip().split("\n")
    # 마지막 해시태그 줄들을 찾아 그 앞에 삽입
    idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if s.startswith("#"):
            idx = i
        elif s:
            break
    head, tail = lines[:idx], lines[idx:]
    while head and not head[-1].strip():
        head.pop()
    parts = ["\n".join(head).rstrip(), cta]
    if tail:
        parts.append("\n".join(tail).strip())
    return "\n\n".join(p for p in parts if p)


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
    g.add_argument("--diagnose", metavar="KEY",
                   help="발행 없이 컨테이너→업로드→처리까지만(전체 응답 덤프). 발행된 것도 지정 가능")
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
        if _os.environ.get("IG_TOKEN"):
            tok = {"access_token": _os.environ["IG_TOKEN"],
                   "ig_user_id": _os.environ.get("IG_USER_ID") or "",   # 빈값이면 아래서 자동탐색
                   "ig_username": _os.environ.get("IG_USERNAME", "leehyun_calc")}
        else:
            sys.exit("token.json/IG_TOKEN 없음 — get_ig_token.py 또는 GitHub Secrets 설정")
    # ig_user_id 미지정 시 토큰으로 자동 발견(/me/accounts -> instagram_business_account)
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

    if args.diagnose:
        # 발행 없이 업로드 파이프라인만 검증(공개 부작용 없음 — media_publish 안 함)
        target = next((r for r in reels if r.get("key") == args.diagnose or r["file"] == args.diagnose), None)
        if not target:
            sys.exit(f"diagnose 대상 없음: {args.diagnose}")
        path = os.path.join(cfg["video_dir"], target["file"])
        print(f"🔬 진단: {target['file']}  ({os.path.getsize(path)/1e6:.1f}MB)")
        try:
            cid = upload_container(tok["ig_user_id"], tok["access_token"], path,
                                   with_cta(target.get("caption", "")), verbose=True)
            print(f"    ✅ 진단 통과(FINISHED, 발행 안 함): 컨테이너 {cid}")
        except Exception as e:
            print(f"    ❌ 진단 실패: {e}")
            sys.exit(1)
        return

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
    failed = []                               # ★ 실패 시 exit 1 → Actions 런이 빨갛게 뜸(무성실패 방지)
    for r in todo:
        path = os.path.join(vdir, r["file"])
        if not os.path.exists(path):
            print(f"⚠️  파일 없음, 건너뜀: {r['file']}")
            failed.append(r["file"])
            continue
        print(f"⬆️  {r['file']}")
        try:
            mid = publish_reel(ig, token, path, with_cta(r.get("caption", "")))
            state[r["file"]] = {"mediaId": mid, "at": now.isoformat()}
            save_state(state)
            print(f"    ✅ 발행 완료 mediaId: {mid}")
            # CTA 댓글: ⚠️ IG Graph API는 '자기 게시물에 최상위 댓글 작성'을 지원하지 않음.
            #   (2026-07-25 검증: 토큰에 instagram_manage_comments 있어도 (#10) permission 에러.
            #    그 권한은 남의 댓글 조회/답글/숨김용이지 새 댓글 작성용이 아님.)
            #   → CTA는 캡션(with_cta)이 정본. 아래는 IG가 나중에 지원할 때를 위해 남겨둔 옵트인 경로.
            if os.environ.get("IG_TRY_COMMENT") == "1":
              try:
                  cmt = post_comment(mid, token)
                  state[r["file"]]["commentId"] = cmt
                  save_state(state)
                  print(f"    💬 CTA 댓글 완료: {cmt}")
              except Exception as e:
                  print(f"    ⚠️ 댓글 실패(발행은 성공): {e}")
        except requests.HTTPError as e:
            print(f"    ❌ 실패: {e.response.text[:300]}")
            failed.append(r["file"])
        except Exception as e:
            print(f"    ❌ 실패: {e}")
            failed.append(r["file"])
    # ★ 밀린 것(publishAt<now인데 미발행) 잔존 검사 — 실패·스킵이 조용히 묻히는 걸 막는다
    overdue = [r["file"] for r in reels
               if not r.get("skip") and r["file"] not in state and r.get("publishAt")
               and datetime.fromisoformat(r["publishAt"]) <= now]
    print("끝. 상태는 published.json 참고.")
    if failed or overdue:
        print(f"🚨 실패 {len(failed)}건 {failed} / 밀림 {len(overdue)}건 {overdue}")
        sys.exit(1)


if __name__ == "__main__":
    main()
