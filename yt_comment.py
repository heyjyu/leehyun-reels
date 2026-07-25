#!/usr/bin/env python3
"""이현 미적분 채널의 공개된 롱폼·쇼츠에 CTA 댓글을 자동으로 단다.
- GitHub Actions 매일 cron. 채널 업로드 목록을 훑어 공개+미달림 영상에 댓글.
- 롱폼(제목에 '|', '#shorts' 없음): 정식강의+전자책 CTA.
- 쇼츠(제목에 '#shorts'): 제목 키워드로 관련 시리즈 재생목록을 찾아 '풀강의로' 유도(쇼츠→롱폼).
    · 매칭 규칙 없으면 스킵(상태에 기록 안 함) → 나중에 규칙/재생목록 준비되면 그때 달림.
- 중복방지: yt_commented.json {videoId: commentId} (repo 커밋).
- 고정(핀)은 API 불가 → 댓글만.
사용: python yt_comment.py [--list]
env: YT_TOKEN = youtube-uploader/token.json 내용(JSON) 통째로.
"""
import json, os, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
COURSE = os.environ.get("YT_COURSE", "11473")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_commented.json")

# 쇼츠 → 관련 시리즈 재생목록 매핑(제목 키워드 첫 매칭). 재생목록 존재하는 것만.
# 순서 중요(위에서부터 검사). 새 시리즈 재생목록 생기면 여기 추가.
SHORTS_RULES = [
    {"kw": ["사이클로이드", "매개곡선"], "pid": "PLSAVdFPMAhEY", "name": "매개곡선 완전정복"},
    {"kw": ["극곡선", "극좌표", "장미곡선", "카디오이드"], "pid": "PLcR1LhsKtrdc", "name": "극좌표 완전정복"},
    {"kw": ["공간좌표", "벡터", "내적", "외적", "삼중곱", "단위벡터", "정사영", "3D", "3차원", "성분"],
     "pid": "PLUTKgS90qcvo", "name": "공간좌표와 벡터 완전정복"},
]

def longform_comment(course):
    return (
        "이 영상이 도움이 되셨다면 👇\n\n"
        "강의 전체를 제대로 배우고 싶다면\n"
        f"🎓 미적분학2 정식 강의(35강) → https://www.unistudy.co.kr/course/detail/{course}\n\n"
        "수학이 막막하게 느껴진다면\n"
        "📚 이현 전자책·수학 진단 → https://leehyunmath.com/\n\n"
        "궁금한 점은 편하게 댓글 남겨주세요!"
    )

def shorts_comment(rule):
    return (
        "이 개념, 풀버전 강의로 제대로 잡고 싶다면 👇\n"
        f"▶ {rule['name']} (재생목록) → https://www.youtube.com/playlist?list={rule['pid']}\n"
        "📚 이현 전자책·수학 진단 → https://leehyunmath.com/"
    )

def match_short_rule(title):
    for r in SHORTS_RULES:
        if any(k in title for k in r["kw"]):
            return r
    return None

def service():
    info = json.loads(os.environ["YT_TOKEN"])
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

def load_state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}

def is_longform(title):
    return ("|" in title) and ("#shorts" not in title.lower())

def is_short(title):
    return "#shorts" in title.lower()

def main():
    list_only = "--list" in sys.argv[1:]
    yt = service()
    state = load_state()

    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, req = [], yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50)
    while req and len(ids) < 300:
        res = req.execute()
        ids += [it["contentDetails"]["videoId"] for it in res.get("items", [])]
        req = yt.playlistItems().list_next(req, res)

    todo = []  # (vid, title, text)
    for i in range(0, len(ids), 50):
        vres = yt.videos().list(part="snippet,status", id=",".join(ids[i:i+50])).execute()
        for it in vres["items"]:
            vid, st, title = it["id"], it["status"]["privacyStatus"], it["snippet"]["title"]
            if st != "public" or vid in state:
                continue
            if is_longform(title):
                todo.append((vid, title, longform_comment(COURSE)))
            elif is_short(title):
                rule = match_short_rule(title)
                if rule:
                    todo.append((vid, title, shorts_comment(rule)))
                # 규칙 없으면 스킵(기록 안 함) — 재생목록 준비되면 다음 회차에 달림

    if not todo:
        print("댓글 달 신규 공개 영상 없음. (전부 처리됨/예약중/규칙대기)"); return
    if list_only:
        print("대상(미달림):"); [print(" -", v, t[:40]) for v, t, _ in todo]; return

    for vid, title, text in todo:
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
