"""
Maple Cold Caller Match Engine — Tornado Web App
Run: python3 app.py [--port=8888]
"""
import tornado.ioloop
import tornado.web
import tornado.options
import os
import json
import csv
import io
import hashlib
import db
import ai

tornado.options.define("port", default=8888, help="port to listen on", type=int)

TMPL = os.path.join(os.path.dirname(__file__), "templates")


# ──────────────────────────────────────────────────────────────────────────────
# Base Handler
# ──────────────────────────────────────────────────────────────────────────────

_APP_PASSWORD = os.environ.get("MAPLE_APP_PASSWORD", "")


class Base(tornado.web.RequestHandler):
    def get_current_user(self):
        if not _APP_PASSWORD:
            return "open"  # no password set → open access
        return self.get_secure_cookie("maple_user")

    def prepare(self):
        if not _APP_PASSWORD:
            return  # auth disabled
        if not self.get_current_user():
            if self.request.path not in ("/login",):
                self.redirect("/login")
                return

    def get_arg(self, name, default='', type=None):
        val = self.get_argument(name, None)
        if val is None:
            return default
        val = val.strip()
        if type is not None and val:
            try:
                return type(val)
            except (ValueError, TypeError):
                return default
        return val if val else default

    def write_json(self, data, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(data))

    def body_json(self):
        try:
            return json.loads(self.request.body)
        except Exception:
            return {}


class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        if not _APP_PASSWORD:
            self.redirect("/dashboard"); return
        if self.get_secure_cookie("maple_user"):
            self.redirect("/dashboard"); return
        self.render("login.html", error=None)

    def post(self):
        password = self.get_argument("password", "")
        if password == _APP_PASSWORD:
            self.set_secure_cookie("maple_user", "rutger", expires_days=30)
            self.redirect(self.get_argument("next", "/dashboard"))
        else:
            self.render("login.html", error="Incorrect password.")


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie("maple_user")
        self.redirect("/login")


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

class DashboardHandler(Base):
    def get(self):
        stats = db.get_dashboard_stats()
        self.render("dashboard.html", stats=stats, page='dashboard')


# ──────────────────────────────────────────────────────────────────────────────
# Client Campaigns
# ──────────────────────────────────────────────────────────────────────────────

class CampaignListHandler(Base):
    def get(self):
        search = self.get_arg('q')
        status = self.get_arg('status')
        campaigns = db.get_campaigns(search=search, status=status)
        self.render("campaigns/list.html", campaigns=campaigns, search=search,
                    status=status, page='campaigns')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        cid = db.create_campaign(data)
        self.redirect(f'/campaigns/{cid}')


class CampaignNewHandler(Base):
    def get(self):
        self.render("campaigns/form.html", campaign=None, page='campaigns')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        cid = db.create_campaign(data)
        self.redirect(f'/campaigns/{cid}')


class CampaignDetailHandler(Base):
    def get(self, cid):
        campaign = db.get_campaign(int(cid))
        if not campaign:
            self.send_error(404); return
        profiles = db.get_profiles(campaign_id=int(cid))
        match_scores = db.get_match_scores(campaign_id=int(cid))
        outreach = db.get_outreach_queue(campaign_id=int(cid))
        interviews = db.get_interview_queue(campaign_id=int(cid))
        self.render("campaigns/detail.html", campaign=campaign, profiles=profiles,
                    match_scores=match_scores, matches=match_scores,
                    outreach=outreach, interviews=interviews, page='campaigns')


class CampaignEditHandler(Base):
    def get(self, cid):
        campaign = db.get_campaign(int(cid))
        if not campaign:
            self.send_error(404); return
        self.render("campaigns/form.html", campaign=campaign, page='campaigns')

    def post(self, cid):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        db.update_campaign(int(cid), data)
        self.redirect(f'/campaigns/{cid}')


class CampaignDeleteHandler(Base):
    def post(self, cid):
        db.delete_campaign(int(cid))
        self.redirect('/campaigns')


# ──────────────────────────────────────────────────────────────────────────────
# Ideal Caller Profiles
# ──────────────────────────────────────────────────────────────────────────────

class ProfileListHandler(Base):
    def get(self):
        campaign_id = self.get_arg('campaign_id') or None
        if campaign_id:
            campaign_id = int(campaign_id)
        profiles = db.get_profiles(campaign_id=campaign_id)
        campaigns = db.get_campaigns()
        self.render("profiles/list.html", profiles=profiles, campaigns=campaigns,
                    selected_campaign=campaign_id, page='profiles')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        pid = db.create_profile(data)
        self.redirect(f'/profiles/{pid}')


class ProfileNewHandler(Base):
    def get(self):
        campaigns = db.get_campaigns()
        campaign_id = self.get_arg('campaign_id')
        self.render("profiles/form.html", profile=None, campaigns=campaigns,
                    preselect_campaign=campaign_id, page='profiles')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        pid = db.create_profile(data)
        self.redirect(f'/profiles/{pid}')


class ProfileDetailHandler(Base):
    def get(self, pid):
        profile = db.get_profile(int(pid))
        if not profile:
            self.send_error(404); return
        self.render("profiles/detail.html", profile=profile, page='profiles')


class ProfileEditHandler(Base):
    def get(self, pid):
        profile = db.get_profile(int(pid))
        if not profile:
            self.send_error(404); return
        campaigns = db.get_campaigns()
        self.render("profiles/form.html", profile=profile, campaigns=campaigns,
                    preselect_campaign='', page='profiles')

    def post(self, pid):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        db.update_profile(int(pid), data)
        self.redirect(f'/profiles/{pid}')


class ProfileDeleteHandler(Base):
    def post(self, pid):
        db.delete_profile(int(pid))
        self.redirect('/profiles')


# ──────────────────────────────────────────────────────────────────────────────
# Candidates
# ──────────────────────────────────────────────────────────────────────────────

class CandidateListHandler(Base):
    def get(self):
        search = self.get_arg('q')
        status = self.get_arg('status')
        platform = self.get_arg('platform')
        candidates = db.get_candidates(search=search, status=status, platform=platform)
        self.render("candidates/list.html", candidates=candidates, search=search,
                    status=status, platform=platform, page='candidates')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        cid = db.create_candidate(data)
        self.redirect(f'/candidates/{cid}')


class CandidateNewHandler(Base):
    def get(self):
        self.render("candidates/form.html", candidate=None, page='candidates')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        cid = db.create_candidate(data)
        self.redirect(f'/candidates/{cid}')


class CandidateDetailHandler(Base):
    def get(self, cid):
        candidate = db.get_candidate(int(cid))
        if not candidate:
            self.send_error(404); return
        match_scores = db.get_match_scores(candidate_id=int(cid))
        outreach = db.get_outreach_queue()
        outreach = [o for o in outreach if o['candidate_id'] == int(cid)]
        interviews = db.get_interview_queue()
        interviews = [i for i in interviews if i['candidate_id'] == int(cid)]
        self.render("candidates/detail.html", candidate=candidate, match_scores=match_scores,
                    outreach=outreach, interviews=interviews, page='candidates')


class CandidateEditHandler(Base):
    def get(self, cid):
        candidate = db.get_candidate(int(cid))
        if not candidate:
            self.send_error(404); return
        self.render("candidates/form.html", candidate=candidate, page='candidates')

    def post(self, cid):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        db.update_candidate(int(cid), data)
        self.redirect(f'/candidates/{cid}')


class CandidateDeleteHandler(Base):
    def post(self, cid):
        db.delete_candidate(int(cid))
        self.redirect('/candidates')


class CandidateStatusHandler(Base):
    """AJAX endpoint: POST /api/candidates/{id}/status  body: {"status": "placed"}"""
    def post(self, cid):
        data = self.body_json()
        status = data.get('status', '')
        VALID = {'found','contacted','replied','qualified','interview','placed','rejected'}
        if status not in VALID:
            self.write_json({'error': 'invalid status'}, 400); return
        db.update_candidate_status(int(cid), status)
        self.write_json({'ok': True, 'status': status})


# ──────────────────────────────────────────────────────────────────────────────
# Candidate Match Scores
# ──────────────────────────────────────────────────────────────────────────────

class MatchScoreListHandler(Base):
    def get(self):
        campaign_id = self.get_arg('campaign_id') or None
        if campaign_id:
            campaign_id = int(campaign_id)
        matches = db.get_match_scores(campaign_id=campaign_id)
        campaigns = db.get_campaigns()
        self.render("matches/list.html", matches=matches, campaigns=campaigns,
                    selected_campaign=campaign_id, page='matches')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        mid = db.create_match_score(data)
        self.redirect(f'/matches/{mid}')


class MatchScoreNewHandler(Base):
    def get(self):
        campaigns = db.get_campaigns()
        candidates = db.get_candidates()
        preselect_candidate = self.get_arg('candidate_id', type=int)
        preselect_campaign  = self.get_arg('campaign_id',  type=int)
        profiles = db.get_profiles(campaign_id=preselect_campaign) if preselect_campaign else db.get_profiles()
        self.render("matches/form.html", match=None, campaigns=campaigns,
                    candidates=candidates, profiles=profiles,
                    preselect_candidate=preselect_candidate,
                    preselect_campaign=preselect_campaign, page='matches')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        mid = db.create_match_score(data)
        self.redirect(f'/matches/{mid}')


class MatchScoreDetailHandler(Base):
    def get(self, mid):
        match = db.get_match_score(int(mid))
        if not match:
            self.send_error(404); return
        self.render("matches/detail.html", match=match, page='matches')


class MatchScoreEditHandler(Base):
    def get(self, mid):
        match = db.get_match_score(int(mid))
        if not match:
            self.send_error(404); return
        campaigns = db.get_campaigns()
        candidates = db.get_candidates()
        profiles = db.get_profiles(campaign_id=match.get('campaign_id'))
        self.render("matches/form.html", match=match, campaigns=campaigns,
                    candidates=candidates, profiles=profiles,
                    preselect_candidate=None, preselect_campaign=None, page='matches')

    def post(self, mid):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        db.update_match_score(int(mid), data)
        self.redirect(f'/matches/{mid}')


class MatchScoreDeleteHandler(Base):
    def post(self, mid):
        db.delete_match_score(int(mid))
        self.redirect('/matches')


# ──────────────────────────────────────────────────────────────────────────────
# Outreach Queue
# ──────────────────────────────────────────────────────────────────────────────

class OutreachListHandler(Base):
    def get(self):
        campaign_id = self.get_arg('campaign_id') or None
        if campaign_id:
            campaign_id = int(campaign_id)
        status = self.get_arg('status')
        outreach = db.get_outreach_queue(campaign_id=campaign_id, status=status)
        campaigns = db.get_campaigns()
        self.render("outreach/list.html", outreach=outreach, campaigns=campaigns,
                    selected_campaign=campaign_id, status=status, page='outreach')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        oid = db.create_outreach(data)
        self.redirect(f'/outreach/{oid}')


class OutreachNewHandler(Base):
    def get(self):
        campaigns = db.get_campaigns()
        candidates = db.get_candidates()
        preselect_candidate = self.get_arg('candidate_id', type=int)
        preselect_campaign  = self.get_arg('campaign_id',  type=int)
        self.render("outreach/form.html", outreach=None, campaigns=campaigns,
                    candidates=candidates, preselect_candidate=preselect_candidate,
                    preselect_campaign=preselect_campaign, page='outreach')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        oid = db.create_outreach(data)
        self.redirect(f'/outreach/{oid}')


class OutreachDetailHandler(Base):
    def get(self, oid):
        outreach = db.get_outreach(int(oid))
        if not outreach:
            self.send_error(404); return
        self.render("outreach/detail.html", outreach=outreach, page='outreach')


class OutreachEditHandler(Base):
    def get(self, oid):
        outreach = db.get_outreach(int(oid))
        if not outreach:
            self.send_error(404); return
        campaigns = db.get_campaigns()
        candidates = db.get_candidates()
        self.render("outreach/form.html", outreach=outreach, campaigns=campaigns,
                    candidates=candidates, preselect_candidate=None,
                    preselect_campaign=None, page='outreach')

    def post(self, oid):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        db.update_outreach(int(oid), data)
        self.redirect(f'/outreach/{oid}')


class OutreachDeleteHandler(Base):
    def post(self, oid):
        db.delete_outreach(int(oid))
        self.redirect('/outreach')


class OutreachStatusHandler(Base):
    """AJAX: POST /api/outreach/{id}/status  body: {"status": "sent"}"""
    def post(self, oid):
        data = self.body_json()
        status = data.get('status', '')
        VALID = {'pending','sent','replied','qualified','booked','closed'}
        if status not in VALID:
            self.write_json({'error': 'invalid status'}, 400); return
        db.update_outreach_status(int(oid), status)
        self.write_json({'ok': True, 'status': status})


# ──────────────────────────────────────────────────────────────────────────────
# Interview Queue
# ──────────────────────────────────────────────────────────────────────────────

class InterviewListHandler(Base):
    def get(self):
        campaign_id = self.get_arg('campaign_id') or None
        if campaign_id:
            campaign_id = int(campaign_id)
        status = self.get_arg('status')
        interviews = db.get_interview_queue(campaign_id=campaign_id, status=status)
        campaigns = db.get_campaigns()
        self.render("interviews/list.html", interviews=interviews, campaigns=campaigns,
                    selected_campaign=campaign_id, status=status, page='interviews')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        iid = db.create_interview(data)
        self.redirect(f'/interviews/{iid}')


class InterviewNewHandler(Base):
    def get(self):
        campaigns = db.get_campaigns()
        candidates = db.get_candidates()
        preselect_candidate = self.get_arg('candidate_id', type=int)
        preselect_campaign  = self.get_arg('campaign_id',  type=int)
        self.render("interviews/form.html", interview=None, campaigns=campaigns,
                    candidates=candidates, preselect_candidate=preselect_candidate,
                    preselect_campaign=preselect_campaign, page='interviews')

    def post(self):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        iid = db.create_interview(data)
        self.redirect(f'/interviews/{iid}')


class InterviewDetailHandler(Base):
    def get(self, iid):
        interview = db.get_interview(int(iid))
        if not interview:
            self.send_error(404); return
        self.render("interviews/detail.html", interview=interview, page='interviews')


class InterviewEditHandler(Base):
    def get(self, iid):
        interview = db.get_interview(int(iid))
        if not interview:
            self.send_error(404); return
        campaigns = db.get_campaigns()
        candidates = db.get_candidates()
        self.render("interviews/form.html", interview=interview, campaigns=campaigns,
                    candidates=candidates, page='interviews')

    def post(self, iid):
        data = {k: self.get_argument(k, '') for k in self.request.arguments}
        data = {k: v[0].decode() if isinstance(v, list) else v for k, v in data.items()}
        db.update_interview(int(iid), data)
        self.redirect(f'/interviews/{iid}')


class InterviewDeleteHandler(Base):
    def post(self, iid):
        db.delete_interview(int(iid))
        self.redirect('/interviews')


class InterviewStatusHandler(Base):
    def post(self, iid):
        data = self.body_json()
        status = data.get('status', '')
        VALID = {'scheduled','completed','cancelled','no_show'}
        if status not in VALID:
            self.write_json({'error': 'invalid status'}, 400); return
        db.update_interview_status(int(iid), status)
        self.write_json({'ok': True, 'status': status})


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — AI Scoring
# ──────────────────────────────────────────────────────────────────────────────

class AICandidateScoreHandler(Base):
    """POST /api/candidates/{id}/ai-score → runs AI scoring, saves result."""
    def post(self, cid):
        candidate = db.get_candidate(int(cid))
        if not candidate:
            self.write_json({'error': 'not found'}, 404); return
        result, err = ai.score_candidate(candidate)
        if err:
            self.write_json({'error': err}, 500); return
        score = result.get('score', 0)
        db.update_candidate_ai_score(int(cid), score, json.dumps(result))
        self.write_json({'ok': True, 'score': score, 'result': result})


class AIMatchScoreHandler(Base):
    """POST /api/matches/{id}/ai-score → runs AI match scoring, saves result."""
    def post(self, mid):
        match = db.get_match_score(int(mid))
        if not match:
            self.write_json({'error': 'not found'}, 404); return
        candidate = db.get_candidate(match['candidate_id'])
        campaign = db.get_campaign(match['campaign_id'])
        if not candidate or not campaign:
            self.write_json({'error': 'candidate or campaign not found'}, 404); return
        profiles = db.get_profiles(campaign_id=match['campaign_id'])
        profile = profiles[0] if profiles else None
        result, err = ai.score_match(candidate, campaign, profile)
        if err:
            self.write_json({'error': err}, 500); return
        db.save_ai_match_score(int(mid), result)
        self.write_json({'ok': True, 'result': result})


class AIOutreachGenerateHandler(Base):
    """POST /api/outreach/{id}/ai-generate → generates messages, saves them."""
    def post(self, oid):
        outreach = db.get_outreach(int(oid))
        if not outreach:
            self.write_json({'error': 'not found'}, 404); return
        candidate = db.get_candidate(outreach['candidate_id'])
        campaign = db.get_campaign(outreach['campaign_id'])
        if not candidate or not campaign:
            self.write_json({'error': 'candidate or campaign not found'}, 404); return
        profiles = db.get_profiles(campaign_id=outreach['campaign_id'])
        profile = profiles[0] if profiles else None
        result, err = ai.generate_outreach(candidate, campaign, profile)
        if err:
            self.write_json({'error': err}, 500); return
        db.save_outreach_messages(int(oid), result)
        self.write_json({'ok': True, 'result': result})


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — Bulk Candidate Management
# ──────────────────────────────────────────────────────────────────────────────

class CandidateBulkHandler(Base):
    """POST /candidates/bulk-action  body: action=status|delete, ids=1,2,3 [, value=placed]"""
    def post(self):
        action = self.get_arg('action')
        raw_ids = self.get_argument('ids', '')
        value = self.get_arg('value')
        try:
            ids = [int(i.strip()) for i in raw_ids.split(',') if i.strip().isdigit()]
        except Exception:
            ids = []
        if not ids:
            self.redirect('/candidates'); return
        if action == 'ai_score':
            results = ai.bulk_score_candidates(db.get_candidates())
            for cid, result, err in results:
                if result:
                    db.update_candidate_ai_score(cid, result.get('score', 0), json.dumps(result))
            self.redirect('/candidates')
        else:
            VALID_STATUSES = {'found','contacted','replied','qualified','interview','placed','rejected'}
            if action == 'status' and value not in VALID_STATUSES:
                self.redirect('/candidates'); return
            db.bulk_candidate_action(ids, action, value)
            self.redirect('/candidates')


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — CSV Import
# ──────────────────────────────────────────────────────────────────────────────

class CandidateImportHandler(Base):
    def get(self):
        self.render("import/candidates.html", page='candidates',
                    result=None, errors=[], preview_rows=None, preview_headers=[])

    def post(self):
        files = self.request.files.get('csvfile', [])
        if not files:
            self.render("import/candidates.html", page='candidates',
                        result={'imported': 0, 'skipped': 0, 'errors': ['No file uploaded.']},
                        preview_rows=None, preview_headers=[])
            return
        content = files[0]['body'].decode('utf-8', errors='replace')
        try:
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            self.render("import/candidates.html", page='candidates',
                        result=None, preview_rows=None, preview_headers=[])
            return
        imported, skipped, errors = db.import_candidates(rows)
        preview_headers = list(rows[0].keys()) if rows else []
        preview_rows = [list(r.values()) for r in rows[:5]]
        self.render("import/candidates.html", page='candidates',
                    result={'imported': imported, 'skipped': skipped, 'errors': errors},
                    preview_rows=preview_rows, preview_headers=preview_headers)


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — Daily Recruiter Dashboard
# ──────────────────────────────────────────────────────────────────────────────

class DailyDashboardHandler(Base):
    def get(self):
        from datetime import datetime as _dt
        stats = db.get_daily_stats()
        today = _dt.utcnow().strftime('%A, %B %-d %Y')
        self.render("daily.html", page='daily', stats=stats, today=today, **stats)


# ──────────────────────────────────────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────────────────────────────────────

def make_app():
    db.init_db()
    db.migrate_phase2()
    # Derive cookie secret from password (or use env override); never empty
    _raw_secret = os.environ.get("MAPLE_COOKIE_SECRET") or _APP_PASSWORD or "maple-dev-secret-change-me"
    cookie_secret = hashlib.sha256(_raw_secret.encode()).hexdigest()
    settings = {
        "template_path": TMPL,
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "debug": False,
        "xsrf_cookies": False,
        "cookie_secret": cookie_secret,
    }
    return tornado.web.Application([
        (r"/login",                         LoginHandler),
        (r"/logout",                        LogoutHandler),
        (r"/",                              DashboardHandler),
        (r"/dashboard",                     DashboardHandler),
        (r"/campaigns",                     CampaignListHandler),
        (r"/campaigns/new",                 CampaignNewHandler),
        (r"/campaigns/([0-9]+)",            CampaignDetailHandler),
        (r"/campaigns/([0-9]+)/edit",       CampaignEditHandler),
        (r"/campaigns/([0-9]+)/delete",     CampaignDeleteHandler),
        (r"/profiles",                      ProfileListHandler),
        (r"/profiles/new",                  ProfileNewHandler),
        (r"/profiles/([0-9]+)",             ProfileDetailHandler),
        (r"/profiles/([0-9]+)/edit",        ProfileEditHandler),
        (r"/profiles/([0-9]+)/delete",      ProfileDeleteHandler),
        (r"/candidates",                    CandidateListHandler),
        (r"/candidates/new",                CandidateNewHandler),
        (r"/candidates/([0-9]+)",           CandidateDetailHandler),
        (r"/candidates/([0-9]+)/edit",      CandidateEditHandler),
        (r"/candidates/([0-9]+)/delete",    CandidateDeleteHandler),
        (r"/api/candidates/([0-9]+)/status", CandidateStatusHandler),
        (r"/matches",                       MatchScoreListHandler),
        (r"/matches/new",                   MatchScoreNewHandler),
        (r"/matches/([0-9]+)",              MatchScoreDetailHandler),
        (r"/matches/([0-9]+)/edit",         MatchScoreEditHandler),
        (r"/matches/([0-9]+)/delete",       MatchScoreDeleteHandler),
        (r"/outreach",                      OutreachListHandler),
        (r"/outreach/new",                  OutreachNewHandler),
        (r"/outreach/([0-9]+)",             OutreachDetailHandler),
        (r"/outreach/([0-9]+)/edit",        OutreachEditHandler),
        (r"/outreach/([0-9]+)/delete",      OutreachDeleteHandler),
        (r"/api/outreach/([0-9]+)/status",  OutreachStatusHandler),
        (r"/interviews",                    InterviewListHandler),
        (r"/interviews/new",                InterviewNewHandler),
        (r"/interviews/([0-9]+)",           InterviewDetailHandler),
        (r"/interviews/([0-9]+)/edit",      InterviewEditHandler),
        (r"/interviews/([0-9]+)/delete",    InterviewDeleteHandler),
        (r"/api/interviews/([0-9]+)/status", InterviewStatusHandler),
        (r"/api/candidates/([0-9]+)/ai-score",  AICandidateScoreHandler),
        (r"/api/matches/([0-9]+)/ai-score",     AIMatchScoreHandler),
        (r"/api/outreach/([0-9]+)/ai-generate", AIOutreachGenerateHandler),
        (r"/candidates/bulk-action",            CandidateBulkHandler),
        (r"/import/candidates",                 CandidateImportHandler),
        (r"/daily",                             DailyDashboardHandler),
    ], **settings)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    port = int(os.environ.get("PORT", tornado.options.options.port))
    app = make_app()
    app.listen(port, address="0.0.0.0")
    print(f"Maple Cold Caller running on http://0.0.0.0:{port}")
    tornado.ioloop.IOLoop.current().start()
