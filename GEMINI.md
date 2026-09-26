# 이현 릴스 프로젝트 무중단 자동화 규칙

## 2. 릴스 발행 기술 제약조건 (Strict)
- **해시태그 제한 (Strict)**: 인스타그램 정책 및 Buffer 제약(`Instagram only allows 5 hashtags per post`)에 따라 **해시태그는 포스트당 반드시 최대 5개 이하**로 제한한다.
- **영상 규격**: 15MB 이하 H.264 CRF 23, faststart 압축 유지.
- **커버 썸네일**: 영상 3초 지점(`thumbnailOffset: 3000ms`, 칠판 판서+강사 화면) 지정.
- **영상 호스팅**: GitHub `heyjyu/leehyun-reels`의 master 브랜치 Raw URL(`https://raw.githubusercontent.com/...`) 등 만료되지 않는 영구 스트리밍 URL 사용.
