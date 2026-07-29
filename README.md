# 크라잇에이터

크리에이터가 **이름 · 플랫폼 · 수익**만 입력하면 수수료·세금·정산이 자동 계산됩니다.  
로그인 없이 사용하고, **관리자만** 집계 화면에 로그인합니다.

## 사용법

1. http://localhost:8100 — 활동명 입력 → 불러오기
2. 플랫폼·수익 추가 → 자동 계산
3. **확인** / **입금 완료** 눌러 정산 상태 관리 (풍투데이식 누적)
4. `/login` — 관리자만 (집계·최근 입력)

## 실행

```powershell
copy .env.example .env
python -m pip install -r requirements.txt
python server/app.py
```

## 문구 수정

`data/copy.json` — 디자인은 `styles/app.css`

## 배포

`python scripts/build_release_zip.py` → `CREATIER-RELEASE.zip`
