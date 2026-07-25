#!/usr/bin/env python3
"""이미 발행된 릴스(published.json) 중 CTA 댓글이 없는 것에 소급으로 댓글을 단다.
   commentId가 기록되면 스킵(중복방지). instagram_manage_comments 권한 필요.
사용: python backfill_comments.py [--list]
"""
import json, os, sys
import requests
from reels_upload import GRAPH, IG_CTA_COMMENT, post_comment, load_json, save_state, HERE

def main():
    list_only = "--list" in sys.argv[1:]
    state = load_json("published.json", {}) or {}
    tok = load_json("token.json")
    if not tok and os.environ.get("IG_TOKEN"):
        tok = {"access_token": os.environ["IG_TOKEN"]}
    if not tok:
        sys.exit("token.json / IG_TOKEN 없음")
    token = tok["access_token"]

    # 진단: 토큰에 실제로 부여된 스코프 확인(권한 문제 vs API 미지원 구분용)
    try:
        dbg = requests.get(f"{GRAPH}/debug_token",
                           params={"input_token": token, "access_token": token},
                           timeout=30).json()
        scopes = dbg.get("data", {}).get("scopes", [])
        print("토큰 스코프:", scopes)
        print("instagram_manage_comments 포함:", "instagram_manage_comments" in scopes)
    except Exception as e:
        print("스코프 확인 실패:", e)

    todo = [(f, v) for f, v in state.items() if v.get("mediaId") and not v.get("commentId")]
    if not todo:
        print("댓글 달 발행분 없음(전부 완료)."); return
    print(f"대상 {len(todo)}개:", [f for f, _ in todo])
    if list_only:
        return
    for f, v in todo:
        try:
            cid = post_comment(v["mediaId"], token)
            v["commentId"] = cid
            save_state(state)
            print(f"💬 {f} → {cid}")
        except requests.HTTPError as e:
            print(f"⚠️ {f} 실패: {e.response.text[:250]}")
        except Exception as e:
            print(f"⚠️ {f} 실패: {e}")

if __name__ == "__main__":
    main()
