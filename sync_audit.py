#!/usr/bin/env python3
"""YT 쇼츠 ↔ IG 릴스 예약 싱크 감사.

같은 콘텐츠를 YT(쇼츠)와 IG(릴스)에 같은 날 발행하는 정책( [[leehyun-math-youtube]] )이
지켜지는지 날짜 단위로 대조한다. 불일치가 있으면 exit 1 → 워크플로가 빨갛게 뜨고 알림.

- YT: 채널 업로드 중 제목에 '#shorts' 포함(예약 publishAt 또는 실제 publishedAt)
- IG: config.reels.json의 publishAt (skip=true 제외)
- 비교 창: 오늘-3일 ~ +45일 (KST 날짜 기준). 옛 히스토리는 보지 않음.

사용: python sync_audit.py            # 감사(불일치 시 exit 1)
env: YT_TOKEN = youtube-uploader/token.json 내용(JSON) 통째로.
"""
import json, os, sys
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HERE = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def yt_service():
    info = json.loads(os.environ["YT_TOKEN"])
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def kst_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KST).date()


def main():
    today = datetime.now(KST).date()
    lo, hi = today - timedelta(days=3), today + timedelta(days=45)

    # --- YT 쇼츠 (예약 + 최근 공개)
    yt = yt_service()
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    upl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = []
    req = yt.playlistItems().list(part="contentDetails", playlistId=upl, maxResults=50)
    ids = [i["contentDetails"]["videoId"]
           for i in req.execute().get("items", [])]
    yt_shorts = {}                       # date -> [title]
    for i in range(0, len(ids), 50):
        for v in yt.videos().list(part="snippet,status",
                                  id=",".join(ids[i:i+50])).execute()["items"]:
            title = v["snippet"]["title"]
            if "#shorts" not in title.lower():
                continue
            iso = v["status"].get("publishAt") or v["snippet"].get("publishedAt")
            if not iso:
                continue
            d = kst_date(iso)
            if lo <= d <= hi:
                yt_shorts.setdefault(d, []).append(title[:40])

    # --- IG 릴스 (config)
    cfg = json.load(open(os.path.join(HERE, "config.reels.json"), encoding="utf-8"))
    ig_reels = {}                        # date -> [file]
    for r in cfg["reels"]:
        if r.get("skip") or not r.get("publishAt"):
            continue
        d = kst_date(r["publishAt"])
        if lo <= d <= hi:
            ig_reels.setdefault(d, []).append(r["file"])

    # --- 대조
    problems = []
    for d in sorted(set(yt_shorts) | set(ig_reels)):
        y, g = yt_shorts.get(d, []), ig_reels.get(d, [])
        mark = "OK" if (y and g) else "★불일치"
        print(f"{d}  YT {len(y)}개 {y}  |  IG {len(g)}개 {g}  {mark}")
        if not (y and g):
            problems.append((d, y, g))
    if problems:
        print(f"\n🚨 싱크 불일치 {len(problems)}일:")
        for d, y, g in problems:
            side = "IG 릴스 없음" if y else "YT 쇼츠 없음"
            print(f"  {d}: {side}  (YT={y} IG={g})")
        sys.exit(1)
    print("\n✅ 싱크 정상")


if __name__ == "__main__":
    main()
