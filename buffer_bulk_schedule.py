#!/usr/bin/env python3
"""Buffer를 통해 앞으로의 모든 이현 미적분 릴스를 일괄 예약 등록하는 스크립트."""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

from buffer_scheduler import get_token, get_channels, schedule_reel

HERE = os.path.dirname(os.path.abspath(__file__))

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

    print(f"🚀 Buffer 계정 (@{ig_chan['name']})으로 릴스 예약 일괄 등록 시작...")

    # 등록할 대상: 9월 17일 이후 예정된 릴스 목록
    # (9/14 세 벡터 상자 부피는 이미 발행 완료/처리됨)
    upcoming_reels = [
        r for r in reels if r.get("publishAt") and r["publishAt"] >= "2026-09-17"
    ]

    for r in upcoming_reels:
        fname = r["file"]
        dt = datetime.fromisoformat(r["publishAt"])
        # Buffer GraphQL은 UTC ISO 8601 (YYYY-MM-DDTHH:MM:SS.000Z) 요구
        dt_utc = dt.astimezone(timezone.utc)
        due_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        raw_url = "https://raw.githubusercontent.com/heyjyu/leehyun-reels/master/videos/" + urllib.parse.quote(fname)
        caption = r["caption"]
        if "leehyun_calc" not in caption:
            caption = caption.strip() + "\n\n▶ 자세한 풀강의: 유튜브 leehyun_calc\n📚 정규강의·수학 컨설팅: 프로필 링크"

        print(f"📅 예약 등록 중: {fname}")
        print(f"   - 예정 일시: {r['publishAt']} (UTC: {due_iso})")
        try:
            res = schedule_reel(token, ig_chan["id"], caption, raw_url, due_iso, share_now=False)
            print(f"   ✅ 예약 완료!")
        except Exception as e:
            print(f"   ❌ 실패: {e}")

    print("\n🎉 모든 릴스 예약 등록이 완료되었습니다. Buffer 캘린더에서 확인하실 수 있습니다.")

if __name__ == "__main__":
    main()
