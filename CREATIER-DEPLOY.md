# 크라잇에이터 배포



## Railway (권장)



`CREATIER-RELEASE.zip` 또는 `python scripts/build_release_zip.py`



→ `CREATIER-RAILWAY.md` · `RAILWAY-VARIABLES.txt` · `바로시작.txt` · `CREATIER-출시체크리스트.md`



## 로컬



```powershell

copy .env.example .env

python -m pip install -r requirements.txt

python server/app.py

```



또는 `크라잇에이터시작.bat` (포트 8100 충돌 시 8101~8110 자동)



## 필수 Variables (production)



| 변수 | 예시 |

|------|------|

| CREATIER_ENV | production |

| CREATIER_PUBLIC_URL | https://xxx.up.railway.app |

| AUTH_SECRET | 32자+ 랜덤 |

| CREATIER_ADMIN_EMAIL | 관리자 이메일 |

| CREATIER_ADMIN_PASSWORD | 8자+ |

| CREATIER_DATABASE | /data/creatier.db |

| CREATIER_CONTACT_EMAIL | 문의 이메일 |



**넣지 말 것:** `PORT`, `CREATIER_PORT`, `CREATIER_OAUTH_DEV`



**OAuth (수익 인증):** `META_APP_ID`, `META_APP_SECRET`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`



Volume Mount: `/data`



## 테스트 · 배포 전 확인



```powershell

python -m unittest discover -s tests -v

powershell -File scripts/launch-check.ps1 -Dev

```



Production Variables 설정 후:



```powershell

powershell -File scripts/launch-check.ps1 -StartServer

```

