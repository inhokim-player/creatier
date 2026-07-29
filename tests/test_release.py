"""Creatier release tests."""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

os.environ.setdefault("CREATIER_DATABASE", str(ROOT / "data" / "test-release.db"))
os.environ.setdefault("AUTH_SECRET", "test-secret-32chars-minimum-xxxxx")
os.environ.setdefault("CREATIER_ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("CREATIER_ADMIN_PASSWORD", "adminpass12345")
os.environ.setdefault("CREATIER_OAUTH_DEV", "1")

from app import app  # noqa: E402
from db import init_db, connect  # noqa: E402
from http_security import AUTH_COOKIE, safe_redirect_path  # noqa: E402
from usage_stats import MAX_NAME_CALCS_PER_DAY  # noqa: E402

from datetime import date

init_db()


class CreatierTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with connect() as conn:
            conn.execute("DELETE FROM share_daily WHERE day = ?", (date.today().isoformat(),))
            conn.execute("DELETE FROM platform_sessions")
            conn.execute("DELETE FROM calc_proofs")
            conn.execute("DELETE FROM oauth_states")

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertTrue(r.get_json()["ok"])
        self.assertEqual(r.headers.get("X-Frame-Options"), "DENY")

    def test_safe_redirect(self):
        self.assertEqual(safe_redirect_path("/admin"), "/admin")
        self.assertEqual(safe_redirect_path("//evil.com"), "/admin")
        self.assertEqual(safe_redirect_path("https://evil.com"), "/admin")
        self.assertEqual(safe_redirect_path("/login?x=1"), "/admin")

    def test_admin_requires_auth(self):
        r = self.client.get("/api/admin/overview")
        self.assertEqual(r.status_code, 401)

    def test_admin_cookie_auth(self):
        login = self.client.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "adminpass12345"},
        )
        self.assertTrue(login.get_json()["ok"])
        token = login.get_json()["token"]
        self.client.set_cookie(key=AUTH_COOKIE, value=token)
        r = self.client.get("/api/admin/overview")
        self.assertTrue(r.get_json()["ok"])

    def test_admin_forged_token_rejected(self):
        self.client.set_cookie(key=AUTH_COOKIE, value="forged.token.here")
        r = self.client.get("/api/admin/overview")
        self.assertEqual(r.status_code, 401)

    def _calc(self, name: str, sid: str | None = None):
        sid = sid or f"s-{uuid.uuid4().hex}"
        return self.client.post(
            "/api/calc",
            json={
                "sessionId": sid,
                "creatorName": name,
                "items": [{"platformId": "youtube_ads", "gross": 100000}],
            },
        )

    def test_calc_ephemeral(self):
        r = self._calc(f"테스트{uuid.uuid4().hex[:8]}")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data.get("ephemeral"))
        self.assertIn("creatorName", data)
        self.assertEqual(data["usage"]["dailyNameLimit"], MAX_NAME_CALCS_PER_DAY)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "adminpass12345"},
        )
        ov = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {login.get_json()['token']}"},
        ).get_json()
        self.assertGreater(ov.get("totalNet", 0), 0)

    def test_calc_name_limit_three_per_day(self):
        name = f"유저{uuid.uuid4().hex[:8]}"
        for i in range(MAX_NAME_CALCS_PER_DAY):
            r = self._calc(name, f"loop-{i}-{uuid.uuid4().hex[:6]}")
            self.assertTrue(r.get_json()["ok"], f"calc {i + 1} should succeed")
        r4 = self._calc(name, f"loop-extra-{uuid.uuid4().hex[:6]}")
        data4 = r4.get_json()
        self.assertFalse(data4["ok"])
        self.assertEqual(data4["error"], "name_limit_reached")

    def test_calc_reserved_name_blocked(self):
        r = self._calc("아이유")
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "name_reserved")

    def test_abuse_report(self):
        r = self.client.post(
            "/api/report/abuse",
            json={
                "category": "impersonation",
                "detail": "타인 활동명을 도용해 계산하는 행위를 신고합니다.",
                "contact": "test@example.com",
            },
        )
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("id", data)

    def test_calc_preview(self):
        r = self.client.post(
            "/api/ledger/preview",
            json={"items": [{"platformId": "instagram", "gross": 300000}]},
        )
        data = r.get_json()
        self.assertTrue(data["ok"])
        item = data["items"][0]
        self.assertEqual(item["withholding"], 9900)  # 3.3% of 300000
        self.assertIn("withholdingLabel", item)

    def test_withholding_youtube_none(self):
        from withholding import calc_withholding

        wh = calc_withholding(100000, None)
        self.assertEqual(wh["withholding"], 0)
        self.assertEqual(wh["withholdingType"], "none")

    def test_withholding_instagram_business(self):
        from platforms import net_after_fee

        calc = net_after_fee(1000000, "instagram")
        self.assertEqual(calc["withholding"], 33000)
        self.assertEqual(calc["withholdingType"], "business")
        self.assertEqual(calc["withholdingIncomeTax"], 30000)
        self.assertEqual(calc["withholdingLocalTax"], 3000)

    def test_net_includes_withholding(self):
        from platforms import net_after_fee

        yt = net_after_fee(500_000, "youtube_ads")
        self.assertEqual(yt["withholding"], 0)
        self.assertEqual(yt["net"], 500_000 - yt["platformFee"])

        sp = net_after_fee(1_000_000, "sponsorship")
        self.assertEqual(sp["withholding"], 33_000)
        self.assertEqual(sp["net"], 1_000_000 - sp["platformFee"] - 33_000)

    def test_calc_withholding_multi_platform(self):
        name = f"원천{uuid.uuid4().hex[:8]}"
        r = self.client.post(
            "/api/calc",
            json={
                "sessionId": f"wh-{uuid.uuid4().hex}",
                "creatorName": name,
                "items": [
                    {"platformId": "youtube_ads", "gross": 500000},
                    {"platformId": "sponsorship", "gross": 1000000},
                ],
            },
        )
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["summary"]["ytdWithholding"], 33000)
        # 실수령 = 각 플랫폼 (총수익 − 수수료 − 원천징수) 합
        self.assertEqual(
            data["summary"]["ytdNet"],
            (500_000 - 225_000) + (1_000_000 - 30_000 - 33_000),
        )
        # 과세 수입 = 원천징수 차감 전 (총수익 − 수수료)
        self.assertEqual(data["summary"]["ytdTaxable"], 1_500_000 - 225_000 - 30_000)
        self.assertIn("withholding", data)
        self.assertEqual(data["withholding"]["totalWithholding"], 33000)
        by = {p["platformId"]: p for p in data["withholding"]["byPlatform"]}
        self.assertEqual(by["youtube_ads"]["withholding"], 0)
        self.assertEqual(by["sponsorship"]["withholding"], 33000)

    def test_admin_usage_only(self):
        self._calc(f"관리자테스트{uuid.uuid4().hex[:6]}")
        login = self.client.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "adminpass12345"},
        )
        token = login.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = self.client.get("/api/admin/overview", headers=headers)
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("totalUsers", data)
        self.assertIn("totalNet", data)
        self.assertIn("totalReports", data)
        self.assertNotIn("creatorName", str(data))

    def test_inquiry_report(self):
        r = self.client.post(
            "/api/report/abuse",
            json={
                "category": "inquiry",
                "detail": "서비스 이용 방법에 대해 문의드립니다.",
            },
        )
        self.assertTrue(r.get_json()["ok"])

    def test_documents_for(self):
        r = self.client.get("/api/documents/for?platforms=youtube_ads,tiktok")
        self.assertTrue(r.get_json()["ok"])

    def test_contact_api(self):
        r = self.client.get("/api/contact")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("@", data["email"])

    def test_ads_inquiry(self):
        r = self.client.post(
            "/api/report/abuse",
            json={
                "category": "ads",
                "detail": "브랜드 협찬 및 광고 집행 문의드립니다.",
                "contact": "brand@example.com",
            },
        )
        self.assertTrue(r.get_json()["ok"])

    def _connect_oauth(self, sid: str, platform: str):
        r = self.client.get(f"/oauth/{platform}/start?sessionId={sid}", follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def _calc_with_proof(self, name: str, sid: str, items: list):
        r = self.client.post(
            "/api/calc",
            json={"sessionId": sid, "creatorName": name, "items": items},
            headers={"X-Session-Id": sid},
        )
        data = r.get_json()
        self.assertTrue(data["ok"], data)
        return data

    def test_share_create_and_view(self):
        sid = f"share-{uuid.uuid4().hex[:8]}"
        name = f"공유테스트{uuid.uuid4().hex[:6]}"
        self._connect_oauth(sid, "instagram")
        calc = self._calc_with_proof(name, sid, [{"platformId": "instagram", "gross": 400000}])
        r = self.client.post(
            "/api/share/create",
            json={
                "sessionId": sid,
                "creatorName": name,
                "items": [{"platformId": "instagram", "gross": 400000}],
                "calcProof": calc["calcProof"],
            },
            headers={"X-Session-Id": sid},
        )
        data = r.get_json()
        self.assertTrue(data["ok"], data)
        token = data["shareUrl"].split("/verify/")[-1]
        view = self.client.get(f"/api/share/{token}")
        vdata = view.get_json()
        self.assertTrue(vdata["ok"])
        self.assertEqual(vdata["totals"]["net"], 400000 - 20000 - 13200)

    def test_share_pin(self):
        sid = f"pin-{uuid.uuid4().hex[:8]}"
        name = f"핀테스트{uuid.uuid4().hex[:6]}"
        self._connect_oauth(sid, "tiktok")
        calc = self._calc_with_proof(name, sid, [{"platformId": "tiktok", "gross": 200000}])
        create = self.client.post(
            "/api/share/create",
            json={
                "sessionId": sid,
                "creatorName": name,
                "items": [{"platformId": "tiktok", "gross": 200000}],
                "calcProof": calc["calcProof"],
                "pin": "1234",
            },
            headers={"X-Session-Id": sid},
        ).get_json()
        self.assertTrue(create["ok"], create)
        token = create["shareUrl"].split("/verify/")[-1]
        blocked = self.client.get(f"/api/share/{token}").get_json()
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "pin_required")
        ok = self.client.post(f"/api/share/{token}", json={"pin": "1234"}).get_json()
        self.assertTrue(ok["ok"])

    def test_session_isolation(self):
        sid_a = f"a-{uuid.uuid4().hex[:8]}"
        sid_b = f"b-{uuid.uuid4().hex[:8]}"
        name = f"격리{uuid.uuid4().hex[:6]}"
        self._connect_oauth(sid_a, "instagram")
        calc = self._calc_with_proof(name, sid_a, [{"platformId": "instagram", "gross": 100000}])
        r = self.client.post(
            "/api/share/create",
            json={
                "sessionId": sid_b,
                "creatorName": name,
                "items": [{"platformId": "instagram", "gross": 100000}],
                "calcProof": calc["calcProof"],
            },
            headers={"X-Session-Id": sid_b},
        ).get_json()
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "session_mismatch")


if __name__ == "__main__":
    unittest.main()
