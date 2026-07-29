크라잇에이터 출시 체크리스트 (Railway)

================================



## 배포 전 (로컬)



□ `powershell -File scripts/launch-check.ps1 -Dev` → 테스트 22개 통과

□ `크라잇에이터시작.bat` → http://localhost:8100 (포트 충돌 시 8101~8110 자동)



## GitHub · Railway



□ `CREATIER-RELEASE.zip` 압축 해제 → GitHub 새 저장소 업로드

□ `.env`, `RAILWAY-VARIABLES.txt`, `data/creatier.db` **업로드 금지**

□ Railway → Deploy from GitHub

□ Volume Mount path: `/data`

□ Variables 입력 (`RAILWAY-VARIABLES.txt` 참고)

□ **PORT, CREATIER_PORT, CREATIER_OAUTH_DEV 넣지 않기**

□ Generate Domain → `CREATIER_PUBLIC_URL` 업데이트 → Redeploy



## OAuth (수익 인증 공유)



□ Meta: `META_APP_ID`, `META_APP_SECRET`

□ TikTok: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`

□ Redirect URI 등록:

  - `https://도메인/oauth/instagram/callback`

  - `https://도메인/oauth/tiktok/callback`



## 배포 후 확인



□ `/api/health` → `{"ok":true,"app":"creatier","ready":true}`

□ `/` → 세금 계산 · 원천징수 3.3%

□ `/login` → a123dlsgh@gmail.com 로그인

□ `/admin` → 이용자·누적금액·접수함

□ Instagram/TikTok 연결 → 계산 → 수익 인증 링크

□ `/verify/토큰` → 인증 페이지 · SNS 공유

□ 하단 광고·협업 문의 → a123dlsgh@gmail.com



## 최종 검증 (배포 직전)



□ `powershell -File scripts/launch-check.ps1 -StartServer` → READY + health OK

