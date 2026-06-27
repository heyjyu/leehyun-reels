# leehyun-reels — IG 릴스 자동 발행 (GitHub Actions)

매일 **18:00 KST**에 `publishAt`이 도래한 인스타 릴스를 Graph API로 자동 발행한다.
맥/Business Suite 불필요 — 클라우드(Actions)에서 무인 실행. (heyjyu/coin-alert 패턴)

## 새 릴스 추가하는 법
1. `videos/` 에 9:16 mp4 추가 (파일당 <50MB).
2. `config.reels.json` 의 `reels` 에 한 칸 추가:
   ```json
   { "file": "<videos안의 파일명>", "caption": "캡션...\n#릴스 ...", "publishAt": "2026-07-13T18:00:00+09:00" }
   ```
3. `git add . && git commit && git push`.
→ 그날 18시 Actions가 자동 발행. `published.json`(중복방지)은 Actions가 커밋해 유지.

## 시크릿 (Settings → Secrets and variables → Actions)
- `IG_TOKEN` — IG 시스템 사용자 토큰(만료 없음 권장) 또는 장기 페이지 토큰
- `IG_USER_ID` — IG 비즈니스 계정 ID (leehyun_calc)

## 수동 실행
Actions 탭 → "IG Reels Auto-Publish" → Run workflow → mode 선택
(`--list` 상태만 / `--due` 오늘분 / `--now` 미발행 전부)

## ⚠️ 주의
- Business Suite에 이미 예약한 릴스는 여기 **넣지 말 것**(중복발행). 이 repo는 7/13 이후 신규분 담당.
- 토큰은 절대 커밋 금지(`.gitignore`에 token.json 제외됨, 값은 Secrets로만).
