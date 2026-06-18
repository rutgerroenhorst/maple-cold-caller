"""
Maple Cold Caller Match Engine — Database Layer (SQLite)
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), 'maple_cold_caller.db'))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def to_dict(row):
    return dict(row) if row else None


def to_list(rows):
    return [dict(r) for r in rows]


def now():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS client_campaigns (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name          TEXT NOT NULL,
        niche                TEXT,
        offer_description    TEXT,
        target_market        TEXT,
        language_required    TEXT,
        country_timezone     TEXT,
        pay_structure        TEXT,
        appointment_payout   TEXT,
        closed_deal_bonus    TEXT,
        b2b_or_b2c           TEXT DEFAULT 'B2B',
        gatekeeper_difficulty TEXT,
        required_experience  TEXT,
        preferred_traits     TEXT,
        disqualifiers        TEXT,
        notes                TEXT,
        status               TEXT DEFAULT 'active',
        created_at           TEXT DEFAULT (datetime('now')),
        updated_at           TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ideal_caller_profiles (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id         INTEGER REFERENCES client_campaigns(id) ON DELETE CASCADE,
        profile_summary     TEXT,
        must_have_skills    TEXT,
        nice_to_have_skills TEXT,
        red_flags           TEXT,
        search_keywords     TEXT,
        outreach_angle      TEXT,
        scoring_weights     TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cold_caller_candidates (
        id                             INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name                      TEXT NOT NULL,
        profile_url                    TEXT,
        platform_source                TEXT DEFAULT 'Manual',
        current_role                   TEXT,
        past_sales_roles               TEXT,
        cold_calling_experience        TEXT,
        appointment_setting_experience TEXT,
        d2d_experience                 TEXT,
        b2b_experience                 TEXT,
        gatekeeper_experience          TEXT,
        language_level                 TEXT,
        availability                   TEXT,
        commission_only_fit            INTEGER DEFAULT 0,
        proof_results                  TEXT,
        voice_sample_url               TEXT,
        notes                          TEXT,
        global_score                   INTEGER DEFAULT 0,
        status                         TEXT DEFAULT 'found',
        created_at                     TEXT DEFAULT (datetime('now')),
        updated_at                     TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS candidate_match_scores (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id             INTEGER REFERENCES client_campaigns(id) ON DELETE CASCADE,
        candidate_id            INTEGER REFERENCES cold_caller_candidates(id) ON DELETE CASCADE,
        match_score             INTEGER DEFAULT 0,
        fit_summary             TEXT,
        strengths               TEXT,
        risks                   TEXT,
        recommended_next_action TEXT,
        reject_reason           TEXT,
        created_at              TEXT DEFAULT (datetime('now')),
        updated_at              TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS outreach_queue (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id         INTEGER REFERENCES cold_caller_candidates(id) ON DELETE CASCADE,
        campaign_id          INTEGER REFERENCES client_campaigns(id) ON DELETE CASCADE,
        connection_request   TEXT,
        first_dm             TEXT,
        follow_up_1          TEXT,
        follow_up_2          TEXT,
        qualification_questions TEXT,
        booking_message      TEXT,
        outreach_status      TEXT DEFAULT 'pending',
        next_follow_up_date  TEXT,
        last_message_sent_at TEXT,
        created_at           TEXT DEFAULT (datetime('now')),
        updated_at           TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS interview_queue (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id     INTEGER REFERENCES cold_caller_candidates(id) ON DELETE CASCADE,
        campaign_id      INTEGER REFERENCES client_campaigns(id) ON DELETE CASCADE,
        interview_date   TEXT,
        interview_time   TEXT,
        interviewer      TEXT,
        interview_format TEXT DEFAULT 'Video Call',
        prep_notes       TEXT,
        outcome          TEXT,
        outcome_notes    TEXT,
        status           TEXT DEFAULT 'scheduled',
        created_at       TEXT DEFAULT (datetime('now')),
        updated_at       TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Client Campaigns
# ──────────────────────────────────────────────────────────────────────────────

def get_campaigns(search='', status=''):
    conn = get_db()
    q = "SELECT * FROM client_campaigns WHERE 1=1"
    args = []
    if search:
        q += " AND (client_name LIKE ? OR niche LIKE ? OR target_market LIKE ?)"
        s = f'%{search}%'
        args += [s, s, s]
    if status:
        q += " AND status = ?"
        args.append(status)
    q += " ORDER BY created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_campaign(cid):
    conn = get_db()
    row = to_dict(conn.execute("SELECT * FROM client_campaigns WHERE id=?", (cid,)).fetchone())
    conn.close()
    return row


def create_campaign(data):
    conn = get_db()
    fields = ['client_name','niche','offer_description','target_market','language_required',
              'country_timezone','pay_structure','appointment_payout','closed_deal_bonus',
              'b2b_or_b2c','gatekeeper_difficulty','required_experience','preferred_traits',
              'disqualifiers','notes','status']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    cols = ','.join(fields)
    c = conn.execute(f"INSERT INTO client_campaigns ({cols}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_campaign(cid, data):
    conn = get_db()
    fields = ['client_name','niche','offer_description','target_market','language_required',
              'country_timezone','pay_structure','appointment_payout','closed_deal_bonus',
              'b2b_or_b2c','gatekeeper_difficulty','required_experience','preferred_traits',
              'disqualifiers','notes','status']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), cid]
    conn.execute(f"UPDATE client_campaigns SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_campaign(cid):
    conn = get_db()
    conn.execute("DELETE FROM client_campaigns WHERE id=?", (cid,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Ideal Caller Profiles
# ──────────────────────────────────────────────────────────────────────────────

def get_profiles(campaign_id=None):
    conn = get_db()
    q = """SELECT p.*, c.client_name FROM ideal_caller_profiles p
           LEFT JOIN client_campaigns c ON p.campaign_id = c.id WHERE 1=1"""
    args = []
    if campaign_id:
        q += " AND p.campaign_id=?"
        args.append(campaign_id)
    q += " ORDER BY p.created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_profile(pid):
    conn = get_db()
    row = to_dict(conn.execute(
        "SELECT p.*, c.client_name FROM ideal_caller_profiles p "
        "LEFT JOIN client_campaigns c ON p.campaign_id=c.id WHERE p.id=?", (pid,)).fetchone())
    conn.close()
    return row


def create_profile(data):
    conn = get_db()
    fields = ['campaign_id','profile_summary','must_have_skills','nice_to_have_skills',
              'red_flags','search_keywords','outreach_angle','scoring_weights']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO ideal_caller_profiles ({','.join(fields)}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_profile(pid, data):
    conn = get_db()
    fields = ['campaign_id','profile_summary','must_have_skills','nice_to_have_skills',
              'red_flags','search_keywords','outreach_angle','scoring_weights']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), pid]
    conn.execute(f"UPDATE ideal_caller_profiles SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_profile(pid):
    conn = get_db()
    conn.execute("DELETE FROM ideal_caller_profiles WHERE id=?", (pid,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Cold Caller Candidates
# ──────────────────────────────────────────────────────────────────────────────

def get_candidates(search='', status='', platform=''):
    conn = get_db()
    q = "SELECT * FROM cold_caller_candidates WHERE 1=1"
    args = []
    if search:
        q += " AND (full_name LIKE ? OR current_role LIKE ? OR notes LIKE ?)"
        s = f'%{search}%'
        args += [s, s, s]
    if status:
        q += " AND status=?"
        args.append(status)
    if platform:
        q += " AND platform_source=?"
        args.append(platform)
    q += " ORDER BY global_score DESC, created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_candidate(cid):
    import json as _json
    conn = get_db()
    row = to_dict(conn.execute("SELECT * FROM cold_caller_candidates WHERE id=?", (cid,)).fetchone())
    conn.close()
    if row:
        raw = row.get('ai_score_raw') or ''
        try:
            parsed = _json.loads(raw) if raw else {}
        except Exception:
            parsed = {}
        row['ai_score']      = row.get('global_score') or parsed.get('score')
        row['ai_verdict']    = parsed.get('verdict', '')
        row['ai_summary']    = parsed.get('summary', '')
        row['ai_strengths']  = parsed.get('strengths', '')
        row['ai_weaknesses'] = parsed.get('weaknesses', '')
    return row


def create_candidate(data):
    conn = get_db()
    fields = ['full_name','profile_url','platform_source','current_role','past_sales_roles',
              'cold_calling_experience','appointment_setting_experience','d2d_experience',
              'b2b_experience','gatekeeper_experience','language_level','availability',
              'commission_only_fit','proof_results','voice_sample_url','notes','global_score','status']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO cold_caller_candidates ({','.join(fields)}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_candidate(cid, data):
    conn = get_db()
    fields = ['full_name','profile_url','platform_source','current_role','past_sales_roles',
              'cold_calling_experience','appointment_setting_experience','d2d_experience',
              'b2b_experience','gatekeeper_experience','language_level','availability',
              'commission_only_fit','proof_results','voice_sample_url','notes','global_score','status']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), cid]
    conn.execute(f"UPDATE cold_caller_candidates SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def update_candidate_status(cid, status):
    conn = get_db()
    conn.execute("UPDATE cold_caller_candidates SET status=?, updated_at=? WHERE id=?", (status, now(), cid))
    conn.commit()
    conn.close()


def delete_candidate(cid):
    conn = get_db()
    conn.execute("DELETE FROM cold_caller_candidates WHERE id=?", (cid,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Candidate Match Scores
# ──────────────────────────────────────────────────────────────────────────────

def get_match_scores(campaign_id=None, candidate_id=None):
    conn = get_db()
    q = """SELECT ms.*, c.client_name, ca.full_name as candidate_name, ca.status as candidate_status
           FROM candidate_match_scores ms
           LEFT JOIN client_campaigns c ON ms.campaign_id=c.id
           LEFT JOIN cold_caller_candidates ca ON ms.candidate_id=ca.id
           WHERE 1=1"""
    args = []
    if campaign_id:
        q += " AND ms.campaign_id=?"
        args.append(campaign_id)
    if candidate_id:
        q += " AND ms.candidate_id=?"
        args.append(candidate_id)
    q += " ORDER BY ms.match_score DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_match_score(mid):
    conn = get_db()
    row = to_dict(conn.execute(
        """SELECT ms.*, c.client_name, ca.full_name as candidate_name, '' as profile_name
           FROM candidate_match_scores ms
           LEFT JOIN client_campaigns c ON ms.campaign_id=c.id
           LEFT JOIN cold_caller_candidates ca ON ms.candidate_id=ca.id
           WHERE ms.id=?""", (mid,)).fetchone())
    conn.close()
    return row


def create_match_score(data):
    conn = get_db()
    fields = ['campaign_id','candidate_id','match_score','fit_summary','strengths',
              'risks','recommended_next_action','reject_reason']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO candidate_match_scores ({','.join(fields)}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_match_score(mid, data):
    conn = get_db()
    fields = ['campaign_id','candidate_id','match_score','fit_summary','strengths',
              'risks','recommended_next_action','reject_reason']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), mid]
    conn.execute(f"UPDATE candidate_match_scores SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_match_score(mid):
    conn = get_db()
    conn.execute("DELETE FROM candidate_match_scores WHERE id=?", (mid,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Outreach Queue
# ──────────────────────────────────────────────────────────────────────────────

def get_outreach_queue(campaign_id=None, status=''):
    conn = get_db()
    q = """SELECT oq.*, ca.full_name as candidate_name, c.client_name
           FROM outreach_queue oq
           LEFT JOIN cold_caller_candidates ca ON oq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON oq.campaign_id=c.id
           WHERE 1=1"""
    args = []
    if campaign_id:
        q += " AND oq.campaign_id=?"
        args.append(campaign_id)
    if status:
        q += " AND oq.outreach_status=?"
        args.append(status)
    q += " ORDER BY oq.next_follow_up_date ASC, oq.created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_outreach(oid):
    conn = get_db()
    row = to_dict(conn.execute(
        """SELECT oq.*, ca.full_name as candidate_name, c.client_name
           FROM outreach_queue oq
           LEFT JOIN cold_caller_candidates ca ON oq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON oq.campaign_id=c.id
           WHERE oq.id=?""", (oid,)).fetchone())
    conn.close()
    return row


def create_outreach(data):
    conn = get_db()
    fields = ['candidate_id','campaign_id','connection_request','first_dm','follow_up_1',
              'follow_up_2','qualification_questions','booking_message','outreach_status',
              'next_follow_up_date','last_message_sent_at']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO outreach_queue ({','.join(fields)}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_outreach(oid, data):
    conn = get_db()
    fields = ['candidate_id','campaign_id','connection_request','first_dm','follow_up_1',
              'follow_up_2','qualification_questions','booking_message','outreach_status',
              'next_follow_up_date','last_message_sent_at']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), oid]
    conn.execute(f"UPDATE outreach_queue SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def update_outreach_status(oid, status):
    conn = get_db()
    conn.execute("UPDATE outreach_queue SET outreach_status=?, last_message_sent_at=?, updated_at=? WHERE id=?",
                 (status, now(), now(), oid))
    conn.commit()
    conn.close()


def delete_outreach(oid):
    conn = get_db()
    conn.execute("DELETE FROM outreach_queue WHERE id=?", (oid,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Interview Queue
# ──────────────────────────────────────────────────────────────────────────────

def get_interview_queue(campaign_id=None, status=''):
    conn = get_db()
    q = """SELECT iq.*, ca.full_name as candidate_name, c.client_name
           FROM interview_queue iq
           LEFT JOIN cold_caller_candidates ca ON iq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON iq.campaign_id=c.id
           WHERE 1=1"""
    args = []
    if campaign_id:
        q += " AND iq.campaign_id=?"
        args.append(campaign_id)
    if status:
        q += " AND iq.status=?"
        args.append(status)
    q += " ORDER BY iq.interview_date ASC, iq.interview_time ASC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_interview(iid):
    conn = get_db()
    row = to_dict(conn.execute(
        """SELECT iq.*, ca.full_name as candidate_name, c.client_name
           FROM interview_queue iq
           LEFT JOIN cold_caller_candidates ca ON iq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON iq.campaign_id=c.id
           WHERE iq.id=?""", (iid,)).fetchone())
    conn.close()
    return row


def create_interview(data):
    conn = get_db()
    fields = ['candidate_id','campaign_id','interview_date','interview_time','interviewer',
              'interview_format','prep_notes','outcome','outcome_notes','status']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO interview_queue ({','.join(fields)}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_interview(iid, data):
    conn = get_db()
    fields = ['candidate_id','campaign_id','interview_date','interview_time','interviewer',
              'interview_format','prep_notes','outcome','outcome_notes','status']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), iid]
    conn.execute(f"UPDATE interview_queue SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def update_interview_status(iid, status):
    conn = get_db()
    conn.execute("UPDATE interview_queue SET status=?, updated_at=? WHERE id=?", (status, now(), iid))
    conn.commit()
    conn.close()


def delete_interview(iid):
    conn = get_db()
    conn.execute("DELETE FROM interview_queue WHERE id=?", (iid,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard stats
# ──────────────────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_db()
    stats = {}
    stats['campaigns']    = conn.execute("SELECT COUNT(*) FROM client_campaigns").fetchone()[0]
    stats['active_campaigns'] = conn.execute("SELECT COUNT(*) FROM client_campaigns WHERE status='active'").fetchone()[0]
    stats['profiles']     = conn.execute("SELECT COUNT(*) FROM ideal_caller_profiles").fetchone()[0]
    stats['candidates']   = conn.execute("SELECT COUNT(*) FROM cold_caller_candidates").fetchone()[0]
    stats['placed']       = conn.execute("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='placed'").fetchone()[0]
    stats['in_interview'] = conn.execute("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='interview'").fetchone()[0]
    stats['match_scores'] = conn.execute("SELECT COUNT(*) FROM candidate_match_scores").fetchone()[0]
    stats['outreach']     = conn.execute("SELECT COUNT(*) FROM outreach_queue").fetchone()[0]
    stats['pending_outreach'] = conn.execute("SELECT COUNT(*) FROM outreach_queue WHERE outreach_status='pending'").fetchone()[0]
    stats['interviews']   = conn.execute("SELECT COUNT(*) FROM interview_queue").fetchone()[0]
    stats['scheduled_interviews'] = conn.execute("SELECT COUNT(*) FROM interview_queue WHERE status='scheduled'").fetchone()[0]
    stats['recent_candidates'] = to_list(conn.execute(
        "SELECT * FROM cold_caller_candidates ORDER BY created_at DESC LIMIT 5").fetchall())
    stats['upcoming_interviews'] = to_list(conn.execute(
        """SELECT iq.*, ca.full_name as candidate_name, c.client_name
           FROM interview_queue iq
           LEFT JOIN cold_caller_candidates ca ON iq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON iq.campaign_id=c.id
           WHERE iq.status='scheduled' ORDER BY iq.interview_date ASC LIMIT 5""").fetchall())
    conn.close()
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Phase 2 — AI, Import, Bulk, Daily
# ──────────────────────────────────────────────────────────────────────────────

def migrate_phase2():
    """Add columns introduced in Phase 2. Safe to call multiple times."""
    conn = get_db()
    for sql in [
        "ALTER TABLE cold_caller_candidates ADD COLUMN ai_score_raw TEXT",
        "ALTER TABLE interview_queue ADD COLUMN meeting_link TEXT",
        "ALTER TABLE interview_queue ADD COLUMN interview_result TEXT",
        "ALTER TABLE interview_queue ADD COLUMN notes TEXT",
        "ALTER TABLE outreach_queue ADD COLUMN notes TEXT",
        "ALTER TABLE candidate_match_scores ADD COLUMN status TEXT DEFAULT 'pending'",
        "ALTER TABLE candidate_match_scores ADD COLUMN notes TEXT",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass  # column already exists
    conn.close()


def update_candidate_ai_score(cid: int, score: int, raw_json_str: str):
    conn = get_db()
    conn.execute(
        "UPDATE cold_caller_candidates SET global_score=?, ai_score_raw=?, updated_at=? WHERE id=?",
        (score, raw_json_str, now(), cid)
    )
    conn.commit()
    conn.close()


def save_ai_match_score(mid: int, data: dict):
    """Overwrite all AI-generated fields on a match score row."""
    conn = get_db()
    fields = ['match_score', 'fit_summary', 'strengths', 'risks',
              'recommended_next_action', 'reject_reason']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), mid]
    conn.execute(f"UPDATE candidate_match_scores SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def save_outreach_messages(oid: int, data: dict):
    """Overwrite all 6 message fields on an outreach row."""
    conn = get_db()
    fields = ['connection_request', 'first_dm', 'follow_up_1',
              'follow_up_2', 'qualification_questions', 'booking_message']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), oid]
    conn.execute(f"UPDATE outreach_queue SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def bulk_candidate_action(ids: list, action: str, value: str = None) -> int:
    if not ids:
        return 0
    placeholders = ','.join('?' * len(ids))
    conn = get_db()
    if action == 'status' and value:
        conn.execute(
            f"UPDATE cold_caller_candidates SET status=?, updated_at=? WHERE id IN ({placeholders})",
            [value, now()] + [int(i) for i in ids]
        )
    elif action == 'delete':
        conn.execute(
            f"DELETE FROM cold_caller_candidates WHERE id IN ({placeholders})",
            [int(i) for i in ids]
        )
    count = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    conn.close()
    return count


def import_candidates(rows: list) -> tuple:
    imported, skipped, errors = 0, 0, []
    fields = ['full_name', 'profile_url', 'platform_source', 'current_role', 'past_sales_roles',
              'cold_calling_experience', 'appointment_setting_experience', 'd2d_experience',
              'b2b_experience', 'gatekeeper_experience', 'language_level', 'availability',
              'commission_only_fit', 'proof_results', 'voice_sample_url', 'notes',
              'global_score', 'status']
    placeholders = ','.join(['?'] * len(fields))
    conn = get_db()
    for i, row in enumerate(rows, 1):
        name = row.get('full_name', '').strip()
        if not name:
            skipped += 1
            continue
        try:
            vals = []
            for f in fields:
                v = row.get(f, '')
                if f == 'commission_only_fit':
                    v = 1 if str(v).lower() in ('1', 'yes', 'true') else 0
                elif f == 'global_score':
                    try: v = int(v)
                    except: v = 0
                elif f == 'status':
                    valid = ('found', 'contacted', 'replied', 'qualified', 'interview', 'placed', 'rejected')
                    v = v if v in valid else 'found'
                elif f == 'platform_source':
                    v = v or 'Import'
                vals.append(v)
            conn.execute(
                f"INSERT INTO cold_caller_candidates ({','.join(fields)}) VALUES ({placeholders})",
                vals
            )
            imported += 1
        except Exception as e:
            errors.append(f"Row {i} ({name}): {e}")
    conn.commit()
    conn.close()
    return imported, skipped, errors


def get_daily_stats() -> dict:
    conn = get_db()
    d = {}
    today = datetime.utcnow().strftime('%Y-%m-%d')
    for s in ['found', 'contacted', 'replied', 'qualified', 'interview', 'placed', 'rejected']:
        d[f'status_{s}'] = conn.execute(
            "SELECT COUNT(*) FROM cold_caller_candidates WHERE status=?", (s,)).fetchone()[0]
    d['total_candidates'] = conn.execute("SELECT COUNT(*) FROM cold_caller_candidates").fetchone()[0]
    d['due_followups'] = to_list(conn.execute(
        """SELECT oq.*, ca.full_name as candidate_name, c.client_name
           FROM outreach_queue oq
           LEFT JOIN cold_caller_candidates ca ON oq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON oq.campaign_id=c.id
           WHERE oq.outreach_status NOT IN ('closed','booked')
             AND (oq.next_follow_up_date <= ? OR oq.next_follow_up_date IS NULL OR oq.next_follow_up_date='')
           ORDER BY oq.next_follow_up_date ASC LIMIT 10""", (today,)).fetchall())
    d['todays_interviews'] = to_list(conn.execute(
        """SELECT iq.*, ca.full_name as candidate_name, c.client_name
           FROM interview_queue iq
           LEFT JOIN cold_caller_candidates ca ON iq.candidate_id=ca.id
           LEFT JOIN client_campaigns c ON iq.campaign_id=c.id
           WHERE iq.interview_date=? AND iq.status='scheduled'
           ORDER BY iq.interview_time ASC""", (today,)).fetchall())
    d['top_candidates'] = to_list(conn.execute(
        """SELECT * FROM cold_caller_candidates
           WHERE status NOT IN ('placed','rejected') AND global_score > 0
           ORDER BY global_score DESC LIMIT 8""").fetchall())
    d['recent_placements'] = to_list(conn.execute(
        "SELECT * FROM cold_caller_candidates WHERE status='placed' ORDER BY updated_at DESC LIMIT 5").fetchall())
    d['active_campaigns_list'] = to_list(conn.execute(
        "SELECT * FROM client_campaigns WHERE status='active' ORDER BY created_at DESC LIMIT 5").fetchall())
    d['pending_outreach'] = conn.execute(
        "SELECT COUNT(*) FROM outreach_queue WHERE outreach_status='pending'").fetchone()[0]
    d['scheduled_interviews'] = conn.execute(
        "SELECT COUNT(*) FROM interview_queue WHERE status='scheduled'").fetchone()[0]
    conn.close()
    return d
