"""크라잇에이터 — 수익 입력 · 정산 확인 · 관리자."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from flask import Flask, jsonify, redirect, request, send_from_directory

from auth import (
    attach_auth_cookie,
    clear_auth_cookie,
    get_current_user,
    login as auth_login,
)
from http_security import AUTH_COOKIE, apply_security_headers, client_ip_hash, safe_redirect_path
from db import admin_overview, init_db, sync_platform_admin
from ledger_service import build_dashboard
from platforms import net_after_fee, platform_by_id, platform_list
from security import apply_cloud_defaults, exit_if_misconfigured
from site_copy import load_copy
from tax_documents import build_document_checklist, full_document_guide
from abuse_report import REPORT_CATEGORIES, list_reports, submit_report
from calc_proof import issue_calc_proof
from data_purge import purge_expired
from notify import contact_email
from platform_oauth import (
    complete_oauth,
    disconnect_platform,
    oauth_status,
    start_oauth,
)
from share_verify import create_revenue_share, get_revenue_share
from usage_stats import MAX_NAME_CALCS_PER_DAY, name_usage_today, record_calculation, validate_calc_session

ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__, static_folder=str(ROOT), static_url_path="")


def _load_env_file():
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_env_file()
apply_cloud_defaults()
exit_if_misconfigured()
init_db()
purge_expired()


@app.after_request
def _add_security_headers(response):
    return apply_security_headers(response, request.path)


def _json_error(msg: str, code: int = 400):
    return jsonify({"ok": False, "error": msg}), code


def _require_admin():
    user = get_current_user(
        request.headers.get("Authorization"),
        request.cookies.get(AUTH_COOKIE),
    )
    if not user or user.get("role") != "platform":
        return None, _json_error("unauthorized", 401)
    return user, None


def _entries_from_items(items: list, body: dict | None = None, creator_name: str = "") -> list[dict]:
    entries = []
    for it in items:
        pid = (it.get("platformId") or "").strip()
        gross = float(it.get("gross") or 0)
        if not pid or gross <= 0:
            continue
        entry = _make_ledger_entry(creator_name, pid, gross, body)
        entries.append({k: entry[k] for k in entry if k != "calc"})
    return entries


@app.route("/")
def index():
    return send_from_directory(ROOT, "dashboard.html")


@app.route("/dashboard")
def dashboard_page():
    return send_from_directory(ROOT, "dashboard.html")


@app.route("/login")
def login_page():
    return send_from_directory(ROOT, "login.html")


@app.route("/admin")
def admin_page():
    return send_from_directory(ROOT, "admin.html")


@app.route("/terms")
def terms_page():
    return send_from_directory(ROOT, "terms.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "app": "creatier", "version": "2.0.0", "ready": True})


@app.route("/api/copy")
def api_copy():
    return jsonify({"ok": True, "copy": load_copy()})


@app.route("/api/platforms")
def api_platforms():
    return jsonify({"ok": True, "platforms": platform_list()})


_LOGIN_ERRORS = {
    "invalid_credentials": "이메일 또는 비밀번호가 맞지 않습니다.",
    "too_many_attempts": "로그인 시도가 너무 많습니다. 15분 후 다시 시도하세요.",
}


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    sync_platform_admin()
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    result, err = auth_login(email, body.get("password") or "", request)
    if err:
        msg = _LOGIN_ERRORS.get(err, "로그인할 수 없습니다.")
        code = 429 if err == "too_many_attempts" else 401
        return jsonify({"ok": False, "error": err, "message": msg}), code
    resp = jsonify({"ok": True, **result})
    attach_auth_cookie(resp, result["token"], request)
    return resp


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    resp = jsonify({"ok": True})
    clear_auth_cookie(resp)
    return resp


@app.route("/api/auth/me")
def api_me():
    user, err = _require_admin()
    if err:
        return err
    return jsonify({"ok": True, "user": user})


@app.route("/report")
def report_page():
    return send_from_directory(ROOT, "report.html")


def _public_base_url() -> str:
    env = os.environ.get("CREATIER_PUBLIC_URL", "").strip()
    if env:
        return env.rstrip("/")
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}".rstrip("/")


@app.route("/verify/<path:token>")
def verify_page(token):
    return send_from_directory(ROOT, "verify.html")


_SHARE_ERRORS = {
    "name_required": "활동명을 2자 이상 입력하세요.",
    "name_too_long": "활동명은 40자까지 가능합니다.",
    "name_reserved": "사용할 수 없는 활동명입니다.",
    "no_share_platform": "Instagram 또는 TikTok 수익이 있어야 공유할 수 있습니다.",
    "share_limit_reached": "오늘 공유 링크 생성 한도에 도달했습니다.",
    "pin_invalid": "PIN은 숫자 4자리로 설정하세요.",
    "invalid_token": "유효하지 않은 링크입니다.",
    "not_found": "링크를 찾을 수 없습니다.",
    "expired": "만료된 링크입니다.",
    "revoked": "비활성화된 링크입니다.",
    "view_limit": "조회 한도에 도달했습니다.",
    "pin_required": "PIN이 필요합니다.",
    "pin_wrong": "PIN이 맞지 않습니다.",
    "session_required": "세션이 만료되었습니다. 처음부터 다시 시작하세요.",
    "proof_required": "계산 증명이 필요합니다. 다시 계산 후 공유하세요.",
    "proof_invalid": "유효하지 않은 계산 증명입니다.",
    "proof_used": "이미 사용된 계산입니다. 다시 계산하세요.",
    "proof_expired": "계산 증명이 만료되었습니다. 다시 계산하세요.",
    "session_mismatch": "세션이 일치하지 않습니다. 다른 사람 데이터 접근 차단.",
    "payload_mismatch": "입력 데이터가 계산과 다릅니다.",
    "instagram_auth_required": "Instagram 로그인 연결이 필요합니다.",
    "tiktok_auth_required": "TikTok 로그인 연결이 필요합니다.",
    "oauth_not_configured": "플랫폼 로그인 설정이 필요합니다.",
}


@app.route("/api/contact")
def api_contact():
    email = contact_email()
    return jsonify(
        {
            "ok": True,
            "email": email,
            "mailto": f"mailto:{email}?subject={quote('크라잇에이터 광고·협업 문의')}",
            "reportUrl": "/report?category=ads",
        }
    )


@app.route("/api/oauth/status")
def api_oauth_status():
    session_id = (request.args.get("sessionId") or request.headers.get("X-Session-Id") or "")[:64]
    if not session_id:
        return _json_error("session_required")
    return jsonify({"ok": True, "platforms": oauth_status(session_id)})


@app.route("/oauth/<platform>/start")
def oauth_start(platform):
    session_id = (request.args.get("sessionId") or request.headers.get("X-Session-Id") or "")[:64]
    url, err = start_oauth(platform, session_id)
    if err:
        msg = _SHARE_ERRORS.get(err, "연결할 수 없습니다.")
        return redirect(f"/?oauth_error={err}&platform={platform}")
    return redirect(url)


@app.route("/oauth/<platform>/callback")
def oauth_callback(platform):
    code = request.args.get("code") or ""
    state = request.args.get("state") or ""
    username, err = complete_oauth(platform, code, state)
    if err:
        return redirect(f"/?oauth_error={err}&platform={platform}")
    return redirect(f"/?oauth_ok=1&platform={platform}&user={quote(username or '')}")


@app.route("/api/oauth/<platform>/disconnect", methods=["POST"])
def api_oauth_disconnect(platform):
    body = request.get_json(silent=True) or {}
    session_id = (body.get("sessionId") or request.headers.get("X-Session-Id") or "")[:64]
    if not session_id:
        return _json_error("session_required")
    disconnect_platform(session_id, platform)
    return jsonify({"ok": True})


@app.route("/api/share/create", methods=["POST"])
def api_share_create():
    body = request.get_json(silent=True) or {}
    items = body.get("items") or []
    session_id = (body.get("sessionId") or request.headers.get("X-Session-Id") or "")[:64]
    result, err = create_revenue_share(
        body.get("creatorName") or body.get("name") or "",
        items,
        session_id=session_id,
        calc_proof=body.get("calcProof") or "",
        pin=body.get("pin"),
        ip_hash=client_ip_hash(request),
    )
    if err:
        msg = _SHARE_ERRORS.get(err, "공유 링크를 만들 수 없습니다.")
        code = 429 if err == "share_limit_reached" else 400
        return jsonify({"ok": False, "error": err, "message": msg}), code
    public_url = _public_base_url()
    share_path = f"/verify/{result['token']}"
    return jsonify(
        {
            "ok": True,
            "shareUrl": f"{public_url}{share_path}",
            "sharePath": share_path,
            "expiresInDays": result["expiresInDays"],
            "pinRequired": result["pinRequired"],
            "message": "공유 링크가 생성되었습니다. 7일 후 만료됩니다.",
        }
    )


@app.route("/api/share/<path:token>", methods=["GET", "POST"])
def api_share_view(token):
    body = request.get_json(silent=True) if request.method == "POST" else {}
    pin = (body or {}).get("pin") or request.args.get("pin")
    data, err = get_revenue_share(token, pin=pin)
    if err:
        msg = _SHARE_ERRORS.get(err, "조회할 수 없습니다.")
        code = 403 if err in ("pin_required", "pin_wrong") else 404
        return jsonify({"ok": False, "error": err, "message": msg, "pinRequired": err == "pin_required"}), code
    return jsonify(data)


_CALC_ERRORS = {
    "name_required": "활동명을 2자 이상 입력하세요.",
    "name_too_long": "활동명은 40자까지 가능합니다.",
    "name_reserved": "사용할 수 없는 활동명입니다. 타인 활동명 도용은 신고 대상입니다.",
    "name_limit_reached": f"이 활동명은 오늘 {MAX_NAME_CALCS_PER_DAY}회 계산 한도에 도달했습니다. 내일 다시 이용하세요.",
    "session_used": "이미 계산을 완료했습니다. 처음부터 다시 시작하세요.",
}


_REPORT_ERRORS = {
    "invalid_category": "신고 유형을 선택하세요.",
    "detail_too_short": "신고 내용을 10자 이상 입력하세요.",
    "detail_too_long": "신고 내용은 2000자까지 가능합니다.",
}


@app.route("/api/calc", methods=["POST"])
def api_calc():
    """일회성 계산 — 활동명·금액은 저장하지 않음 · 중복·세션 악용 차단."""
    body = request.get_json(silent=True) or {}
    items = body.get("items") or []
    vat_registered = bool(body.get("vatRegistered"))
    session_id = (body.get("sessionId") or request.headers.get("X-Session-Id") or "")[:64]
    creator_name = (body.get("creatorName") or body.get("name") or "").strip()

    ok, err = validate_calc_session(session_id, creator_name)
    if not ok:
        msg = _CALC_ERRORS.get(err or "", "계산할 수 없습니다.")
        return jsonify({"ok": False, "error": err, "message": msg}), 429 if err in ("session_used", "name_limit_reached") else 400

    entries = _entries_from_items(items, body, creator_name)
    if not entries:
        return _json_error("invalid_input")
    proof = issue_calc_proof(session_id, items, creator_name)
    data = build_dashboard(creator_name, entries, vat_registered=vat_registered)
    tax = data["taxReport"]
    record_calculation(
        session_id,
        creator_name,
        gross=data["summary"].get("ytdGross", 0),
        net=data["summary"].get("ytdNet", 0),
        payable=data["summary"].get("totalPayable", 0),
    )
    used = name_usage_today(creator_name)
    remaining = max(0, MAX_NAME_CALCS_PER_DAY - used)
    return jsonify(
        {
            "ok": True,
            "creatorName": creator_name,
            "usage": {
                "nameUsedToday": used,
                "nameRemainingToday": remaining,
                "dailyNameLimit": MAX_NAME_CALCS_PER_DAY,
            },
            "summary": data["summary"],
            "byPlatform": data["byPlatform"],
            "withholding": data.get("withholding") or tax.get("withholding"),
            "entries": entries,
            "documents": tax["documents"],
            "filingCalendar": tax["filingCalendar"],
            "alerts": tax["alerts"],
            "disclaimer": tax.get("disclaimer"),
            "ephemeral": True,
            "calcProof": proof,
            "oauthStatus": oauth_status(session_id),
        }
    )


@app.route("/api/documents/guide")
def api_documents_guide():
    return jsonify({"ok": True, "guide": full_document_guide()})


@app.route("/api/documents/for")
def api_documents_for():
    raw = (request.args.get("platforms") or "").strip()
    used = {x.strip() for x in raw.split(",") if x.strip()}
    if not used:
        return _json_error("platforms_required")
    vat_registered = request.args.get("vatRegistered", "").lower() in ("1", "true", "yes")
    docs = build_document_checklist(used, vat_registered=vat_registered)
    platforms = []
    for pid in sorted(used):
        spec = platform_by_id(pid)
        if spec:
            platforms.append(
                {
                    "id": pid,
                    "name": spec.name,
                    "taxNote": spec.tax_note,
                    "docHint": spec.doc_hint,
                    "feePercent": round(spec.fee_rate * 100, 1),
                    "settlementLabel": spec.settlement_label,
                }
            )
    return jsonify({"ok": True, "documents": docs, "platforms": platforms})


def _make_ledger_entry(name: str, platform_id: str, gross: float, body: dict | None = None) -> dict:
    from datetime import date, timedelta

    calc = net_after_fee(gross, platform_id)
    spec = platform_by_id(platform_id)
    today = date.today()
    b = body or {}
    entry = {
        "creatorName": name,
        "platformId": platform_id,
        "gross": calc["gross"],
        "platformFee": calc["platformFee"],
        "withholding": calc["withholding"],
        "net": calc["net"],
        "status": "recorded",
        "earnedDate": b.get("earnedDate") or today.isoformat(),
        "expectedDepositDate": (
            b.get("expectedDepositDate")
            or (today + timedelta(days=spec.settlement_lag_days if spec else 30)).isoformat()
        ),
    }
    entry["platform"] = spec.name if spec else platform_id
    entry["withholdingLabel"] = calc["withholdingLabel"]
    entry["withholdingRate"] = calc["withholdingRate"]
    entry["withholdingType"] = calc["withholdingType"]
    entry["withholdingIncomeTax"] = calc["withholdingIncomeTax"]
    entry["withholdingLocalTax"] = calc["withholdingLocalTax"]
    entry["calc"] = calc
    return entry


@app.route("/api/ledger/preview", methods=["POST"])
def api_ledger_preview():
    body = request.get_json(silent=True) or {}
    items = body.get("items") or []
    if not items:
        single = body.get("platformId")
        gross = float(body.get("gross") or 0)
        if single and gross > 0:
            items = [{"platformId": single, "gross": gross}]
    results = []
    total_gross = total_fee = total_wh = total_net = 0
    for it in items:
        pid = (it.get("platformId") or "").strip()
        gross = float(it.get("gross") or 0)
        if not pid or gross <= 0:
            continue
        row = _make_ledger_entry("", pid, gross)
        results.append(
            {
                "platformId": pid,
                "platform": row["platform"],
                "gross": row["gross"],
                "platformFee": row["platformFee"],
                "withholding": row["withholding"],
                "net": row["net"],
            }
        )
        total_gross += row["gross"]
        total_fee += row["platformFee"]
        total_wh += row["withholding"]
        total_net += row["net"]
    if not results:
        return _json_error("invalid_input")
    used = {r["platformId"] for r in results}
    vat_registered = bool(body.get("vatRegistered"))
    docs = build_document_checklist(used, vat_registered=vat_registered)
    for row in results:
        spec = platform_by_id(row["platformId"])
        calc = net_after_fee(row["gross"], row["platformId"])
        row["feeRate"] = calc["feeRate"]
        row["feePercent"] = round(calc["feeRate"] * 100, 1)
        row["withholdingLabel"] = calc["withholdingLabel"]
        row["withholdingRate"] = calc["withholdingRate"]
        row["withholdingType"] = calc["withholdingType"]
        row["withholdingIncomeTax"] = calc["withholdingIncomeTax"]
        row["withholdingLocalTax"] = calc["withholdingLocalTax"]
        row["taxNote"] = spec.tax_note if spec else ""
        row["docHint"] = spec.doc_hint if spec else ""
        row["settlementLabel"] = spec.settlement_label if spec else ""
    return jsonify(
        {
            "ok": True,
            "items": results,
            "totals": {
                "gross": total_gross,
                "platformFee": total_fee,
                "withholding": total_wh,
                "net": total_net,
            },
            "documents": docs,
        }
    )


@app.route("/api/report/categories")
def api_report_categories():
    return jsonify(
        {
            "ok": True,
            "categories": [{"id": k, "label": v} for k, v in REPORT_CATEGORIES.items()],
        }
    )


@app.route("/api/report/abuse", methods=["POST"])
def api_report_abuse():
    body = request.get_json(silent=True) or {}
    result, err = submit_report(
        body.get("category", ""),
        body.get("detail", ""),
        body.get("contact", ""),
    )
    if err:
        msg = _REPORT_ERRORS.get(err, "신고 접수에 실패했습니다.")
        return jsonify({"ok": False, "error": err, "message": msg}), 400
    return jsonify({"ok": True, **result, "message": "신고가 접수되었습니다. 검토 후 필요 시 조치합니다."})


@app.route("/api/admin/reports")
def api_admin_reports():
    _, err = _require_admin()
    if err:
        return err
    return jsonify({"ok": True, "reports": list_reports()})


@app.route("/api/admin/overview")
def api_admin_overview():
    _, err = _require_admin()
    if err:
        return err
    return jsonify({"ok": True, **admin_overview()})


if __name__ == "__main__":
    import socket

    from security import is_cloud_host

    host = "0.0.0.0"
    cloud_port = os.environ.get("PORT", "").strip()

    if cloud_port:
        port = int(cloud_port)
    else:
        preferred = int(os.environ.get("CREATIER_PORT", "8100"))

        def port_available(p: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind((host, p))
                    return True
                except OSError:
                    return False

        port = preferred
        for candidate in range(preferred, preferred + 11):
            if port_available(candidate):
                port = candidate
                break
        else:
            print(f"\n  [오류] 포트 {preferred}~{preferred + 10} 모두 사용 중입니다.")
            print("  작업 관리자에서 python.exe 를 종료하거나 CREATIER_PORT 를 변경하세요.\n")
            raise SystemExit(1)

        if port != preferred:
            os.environ["CREATIER_PORT"] = str(port)
            print(f"\n  [안내] 포트 {preferred} 사용 중 → {port} 로 시작합니다.")

    url = f"http://localhost:{port}" if not is_cloud_host() else os.environ.get("CREATIER_PUBLIC_URL", f"http://0.0.0.0:{port}")
    print(f"\n  Creatier: {url}")
    if not is_cloud_host():
        print(f"  관리자:   http://localhost:{port}/login\n")
    try:
        from waitress import serve

        serve(app, host=host, port=port, threads=4)
    except OSError as e:
        if not cloud_port and (getattr(e, "winerror", None) == 10048 or e.errno in (98, 10048)):
            print(f"\n  [오류] 포트 {port}이(가) 이미 사용 중입니다.")
            print("  크라잇에이터시작.bat 을 다시 실행하면 자동으로 다른 포트를 시도합니다.\n")
        elif cloud_port:
            print(f"\n  [오류] Railway PORT={port} 바인딩 실패. 로그를 확인하세요.\n")
        raise
