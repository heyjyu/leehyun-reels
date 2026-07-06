#!/usr/bin/env python3
"""이현 미적분 채널의 '공개된 롱폼' 중 CTA 댓글이 아직 없는 것에 자동으로 댓글을 단다.
- GitHub Actions 매일 cron 실행. 채널 업로드 목록을 훑어 조건 맞는 것만 댓글.
- 롱폼 판별: privacyStatus=public AND 제목에 '|' 포함(한글 | English) AND '#shorts' 없음.
- 중복방지: yt_commented.json {videoId: commentId} (repo에 커밋).
- 고정(핀)은 API 불가 → 댓글만. (사용자가 원하면 앱에서 수동 고정)
- 강좌링크: 기본 11473(미적분학2, 폴더1·2). 폴더3/4 시작 시 YT_COURSE env로 교체하거나 수동 처리.
사용: python yt_comment.py [--list]      (--list=상태만, 댓글 안 달음)
env: YT_TOKEN = youtube-uploader/token.json 파일 내용(JSON 문자열) 통째로.
"""
import json, os, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
COURSE = os.environ.get("YT_COURSE", "11473")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_commented.json")

def comment_text(course):
    return (
        "이 영상이 도움이 되셨다면 👇\n\n"
        "강의 전체를 제대로 배우고 싶다면\n"
        f"🎓 미적분학2 정식 강의(35강) → https://www.unistudy.co.kr/course/detail/{course}\n\n"
        "수학이 막막하게 느껴진다면\n"
        "📚 이현 전자책·수학 진단 → https://leehyunmath.com/\n\n"
        "궁금한 점은 편하게 댓글 남겨주세요!"
    )

def service():
    info = json.loads(os.environ["YT_TOKEN"])
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def load_state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}

def is_longform(title):
    t = title.lower()
    return ("|" in title) and ("#shorts" not in t)

def main():
    list_only = "--list" in sys.argv[1:]
    yt = service()
    state = load_state()

    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, req = [], yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50)
    while req and len(ids) < 200:
        res = req.execute()
        ids += [it["contentDetails"]["videoId"] for it in res.get("items", [])]
        req = yt.playlistItems().list_next(req, res)

    todo = []
    for i in range(0, len(ids), 50):
        vres = yt.videos().list(part="snippet,status", id=",".join(ids[i:i+50])).execute()
        for it in vres["items"]:
            vid, st, title = it["id"], it["status"]["privacyStatus"], it["snippet"]["title"]
            if st == "public" and is_longform(title) and vid not in state:
                todo.append((vid, title))

    if not todo:
        print("댓글 달 신규 공개 롱폼 없음. (전부 처리됨/예약중)"); return
    if list_only:
        print("대상(미달림):");  [print(" -", v, t[:40]) for v, t in todo]; return

    text = comment_text(COURSE)
    for vid, title in todo:
        try:
            r = yt.commentThreads().insert(
                part="snippet",
                body={"snippet": {"videoId": vid,
                                  "topLevelComment": {"snippet": {"textOriginal": text}}}},
            ).execute()
            state[vid] = r["id"]
            print("✅ 댓글:", vid, "|", title[:34])
        except Exception as e:
            print("⚠️ 실패:", vid, "|", str(e)[:150])
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
