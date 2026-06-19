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


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()[0] > 0


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


def get_candidate_tasks(cid: int) -> list:
    """
    All action_tasks linked to a candidate, ordered: active first
    (Pending → Copied → Sent → Needs Review → Blocked → Rescheduled → Completed → Rejected),
    then by priority, then created_at.
    """
    conn = get_db()
    try:
        rows = to_list(conn.execute("""
            SELECT * FROM action_tasks
            WHERE related_type='candidate' AND related_id=?
            ORDER BY
              CASE status
                WHEN 'Pending'      THEN 0
                WHEN 'Copied'       THEN 1
                WHEN 'Sent'         THEN 2
                WHEN 'Needs Review' THEN 3
                WHEN 'Blocked'      THEN 4
                WHEN 'Rescheduled'  THEN 5
                WHEN 'Completed'    THEN 6
                ELSE 7
              END,
              CASE priority
                WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3
              END,
              created_at ASC
        """, (cid,)).fetchall())
    except Exception:
        rows = []
    conn.close()
    return rows


def get_candidate_source_context(cid: int) -> dict:
    """
    Look up source queue or research queue entry linked to this candidate.
    Returns a dict with optional keys: 'source_queue', 'research_queue'.
    Safe if tables don't exist or fields are missing.
    """
    conn = get_db()
    ctx = {}
    try:
        row = conn.execute(
            "SELECT id, name, source_type, profile_url, score, tier, status, reasons_json "
            "FROM candidate_source_queue WHERE candidate_id=? LIMIT 1",
            (cid,)
        ).fetchone()
        if row:
            ctx['source_queue'] = to_dict(row)
    except Exception:
        pass
    try:
        row = conn.execute(
            "SELECT id, name, source, score, level, status, possible_profile_url, "
            "detected_role, confidence_score, notes "
            "FROM candidate_research_queue WHERE linked_candidate_id=? LIMIT 1",
            (cid,)
        ).fetchone()
        if row:
            ctx['research_queue'] = to_dict(row)
    except Exception:
        pass
    conn.close()
    return ctx


def create_candidate(data):
    conn = get_db()
    fields = ['full_name','profile_url','platform_source','current_role','email','phone',
              'past_sales_roles','cold_calling_experience','appointment_setting_experience',
              'd2d_experience','b2b_experience','gatekeeper_experience','language_level',
              'availability','commission_only_fit','proof_results','voice_sample_url',
              'notes','global_score','status']
    vals = [data.get(f, '') for f in fields]
    placeholders = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO cold_caller_candidates ({','.join(fields)}) VALUES ({placeholders})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_candidate(cid, data):
    conn = get_db()
    fields = ['full_name','profile_url','platform_source','current_role','email','phone',
              'past_sales_roles','cold_calling_experience','appointment_setting_experience',
              'd2d_experience','b2b_experience','gatekeeper_experience','language_level',
              'availability','commission_only_fit','proof_results','voice_sample_url',
              'notes','global_score','status']
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
        "ALTER TABLE cold_caller_candidates ADD COLUMN email TEXT",
        "ALTER TABLE cold_caller_candidates ADD COLUMN phone TEXT",
        "ALTER TABLE interview_queue ADD COLUMN meeting_link TEXT",
        "ALTER TABLE interview_queue ADD COLUMN interview_result TEXT",
        "ALTER TABLE interview_queue ADD COLUMN notes TEXT",
        "ALTER TABLE outreach_queue ADD COLUMN notes TEXT",
        "ALTER TABLE candidate_match_scores ADD COLUMN status TEXT DEFAULT 'pending'",
        "ALTER TABLE candidate_match_scores ADD COLUMN notes TEXT",
        "ALTER TABLE observer_recommendations ADD COLUMN resolved_at TEXT",
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
    fields = ['full_name', 'profile_url', 'platform_source', 'current_role', 'email', 'phone',
              'past_sales_roles', 'cold_calling_experience', 'appointment_setting_experience',
              'd2d_experience', 'b2b_experience', 'gatekeeper_experience', 'language_level',
              'availability', 'commission_only_fit', 'proof_results', 'voice_sample_url',
              'notes', 'global_score', 'status']
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


# ──────────────────────────────────────────────────────────────────────────────
# Growth OS — Agents, Search Missions, Logs, Observer Recommendations
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_ALLOWED = (
    "generate search queries\n"
    "process pasted text\n"
    "score candidates\n"
    "create internal tasks/recommendations\n"
    "prepare messages\n"
    "add candidates to review queue"
)

_DEFAULT_FORBIDDEN = (
    "auto-send LinkedIn connection requests\n"
    "auto-send LinkedIn DMs\n"
    "auto-comment on LinkedIn\n"
    "auto-like/follow on LinkedIn\n"
    "scrape logged-in LinkedIn\n"
    "bypass platform limits"
)

_DEFAULT_AGENTS = [
    {
        'name': 'Signal Hunter Agent', 'type': 'signal_hunter',
        'description': 'Monitors for buying signals and trigger events indicating a good time to reach out to potential cold callers.',
        'instructions': 'Scan for signals that a candidate is actively looking for sales opportunities. Look for: new job posts, LinkedIn activity, profile updates, or keyword matches in pasted content. Flag high-signal candidates for outreach.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Candidate Research Worker', 'type': 'candidate_research',
        'description': 'Generates targeted search queries based on active search missions. Recommends where and how to find the next batch of candidates.',
        'instructions': 'Review all active search missions. For each mission, generate 3–5 targeted LinkedIn/Google search queries. Prioritize missions with the lowest candidate count vs daily_target. Output queries the recruiter can run manually.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Talent Scout Agent', 'type': 'talent_scout',
        'description': 'Reviews the current candidate pool, identifies who needs action, and surfaces the top candidates to move forward.',
        'instructions': 'Review all candidates. Identify: (1) candidates stuck in "found" for too long, (2) high-score candidates with no match score, (3) qualified candidates with no outreach, (4) "replied" candidates needing follow-up. Output a prioritized action list.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Offer Match Agent', 'type': 'offer_match',
        'description': 'Matches qualified candidates to active campaigns based on skills, language, availability, and commission fit.',
        'instructions': 'For each qualified candidate without a match score, compare their profile to all active campaigns. Generate ranked (candidate, campaign) pairs by fit score. Flag pairs with match_score >= quality_threshold as ready to create a match record.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Outreach Operator Agent', 'type': 'outreach_operator',
        'description': 'Prepares outreach messages for candidates in the pipeline. Generates message sequences ready for human review and send.',
        'instructions': 'For each qualified/contacted candidate with no pending outreach, prepare: connection request, first DM, two follow-ups. All messages must be reviewed by a human before sending. Never auto-send. Use Prepare → Review → Human Send → Mark Sent flow.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Follow-up Agent', 'type': 'follow_up',
        'description': 'Detects candidates and outreach items that need a follow-up. Surfaces overdue items and candidates going cold.',
        'instructions': 'Check outreach_queue for items where status is "sent" or "pending" and next_follow_up_date is today or past. Check interview_queue for interviews today. Return a prioritized action list for the recruiter.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Call Script Agent', 'type': 'call_script',
        'description': 'Generates personalized call scripts and talking points for qualified candidates, tailored to the campaign.',
        'instructions': 'For each candidate matched to a campaign, generate: 30-second opener, 3 qualifying questions, value proposition tailored to the candidate\'s background, objection handling for top 3 objections. Scripts must be reviewed before use.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Account Health Agent', 'type': 'account_health',
        'description': 'Monitors active campaigns and flags health issues: no candidates, stale pipeline, missing match scores.',
        'instructions': 'For each active campaign check: number of candidates, average match score, last outreach date, interviews scheduled. Flag campaigns with < 3 candidates, no outreach in 7 days, or no interviews as "at risk".',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Performance Agent', 'type': 'performance',
        'description': 'Tracks key recruitment metrics: sourcing velocity, outreach response rates, interview-to-placement ratio, and pipeline health.',
        'instructions': 'Calculate and summarize: (1) candidates by status, (2) outreach sent vs replied, (3) interviews scheduled vs completed, (4) placements this month, (5) active vs filled campaigns. Highlight any metric below target.',
        'schedule': 'manual', 'requires_human_approval': 1,
    },
    {
        'name': 'Observer Agent', 'type': 'observer',
        'description': 'Watches the full pipeline. Identifies bottlenecks, flags issues, and makes concrete recommendations to unblock recruitment flow.',
        'instructions': 'Review the full pipeline: candidates, campaigns, outreach, interviews, agent logs, and search missions. Identify the single biggest bottleneck. Write a specific, actionable recommendation with the exact fix. Create an observer_recommendation record.',
        'schedule': 'daily', 'requires_human_approval': 0,
    },
]

_DEFAULT_MISSIONS = [
    {
        'name': 'NL Cold Callers',
        'description': 'Find Dutch-speaking B2B cold callers available for commission or hourly freelance work.',
        'target_role': 'Cold Caller / Telefonische Acquisitie',
        'target_language': 'Dutch', 'target_market': 'Netherlands',
        'keywords': 'koude acquisitie\ntelemarketeer\ncold caller\nappointment setter\nafspraken maken\nB2B sales freelance\ntelefoon acquisitie',
        'negative_keywords': 'agency owner\ntrainer\ncoach\nrecruiter',
        'allowed_sources': 'LinkedIn\nFreelancer.nl\nReferrals',
        'forbidden_sources': 'Instagram DM spam\nPaid databases without consent',
        'daily_target': 5, 'quality_threshold': 60, 'status': 'active',
        'instructions': 'Search LinkedIn for Dutch speakers with "koude acquisitie" or "cold calling" in their profile. Target: freelancers, self-employed, or open-to-work. Avoid agencies unless the person is individually approachable.',
    },
    {
        'name': 'Commission Remote Sales',
        'description': 'Find sales professionals comfortable with commission-only or hybrid pay who can work remotely.',
        'target_role': 'Commission Sales / Remote SDR',
        'target_language': 'Dutch / English', 'target_market': 'Netherlands / Belgium',
        'keywords': 'commission only\nno cure no pay\nprovisiebasis\nSDR freelance\nremote sales\noutbound freelance',
        'negative_keywords': 'base salary only\nfull time employee\nno freelance',
        'allowed_sources': 'LinkedIn\nFreelancer.nl\nUpwork',
        'forbidden_sources': 'Instagram DM spam\nPaid databases without consent',
        'daily_target': 3, 'quality_threshold': 55, 'status': 'active',
        'instructions': 'Search for sales professionals who explicitly mention commission-based or no-cure-no-pay work. Must be open to freelance. Filter for Dutch/Belgian market.',
    },
    {
        'name': 'Young Hungry Setters',
        'description': 'Identify ambitious junior appointment setters (0-3 years experience) willing to learn and grow on performance basis.',
        'target_role': 'Junior Appointment Setter / Sales Trainee',
        'target_language': 'Dutch', 'target_market': 'Netherlands',
        'keywords': 'appointment setter\nsales trainee\njunior SDR\nstarter sales\nenthousaiste verkoper\nyoung professional sales',
        'negative_keywords': 'senior\nmanager\ndirector\n10+ years',
        'allowed_sources': 'LinkedIn\nUniversity job boards',
        'forbidden_sources': 'Instagram DM spam\nPaid databases without consent',
        'daily_target': 4, 'quality_threshold': 45, 'status': 'active',
        'instructions': 'Target recent graduates or early-career professionals in sales. Look for internship experience in outbound sales or telemarketing. Coachability matters more than proven results.',
    },
    {
        'name': 'Experienced Closers',
        'description': 'Find senior B2B closers with proven track records who can handle complex sales cycles.',
        'target_role': 'Senior Closer / Account Executive',
        'target_language': 'Dutch / English', 'target_market': 'Netherlands',
        'keywords': 'B2B closer\naccount executive freelance\nclosing specialist\nhigh ticket sales\nenterprise sales freelance\nconsultative selling',
        'negative_keywords': 'inbound only\ncustomer service\nretail',
        'allowed_sources': 'LinkedIn',
        'forbidden_sources': 'Instagram DM spam\nPaid databases without consent',
        'daily_target': 2, 'quality_threshold': 75, 'status': 'paused',
        'instructions': 'Search for senior B2B sales professionals with track record of closing complex deals. Look for: quota attainment figures, deal sizes, SaaS/services/consultancy background. Commission structure must be attractive.',
    },
]


def init_agents_tables():
    """Create Growth OS tables and seed defaults if empty."""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS agents (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        name                    TEXT NOT NULL,
        type                    TEXT,
        description             TEXT,
        status                  TEXT DEFAULT 'idle',
        enabled                 INTEGER DEFAULT 1,
        last_run_at             TEXT,
        latest_output           TEXT,
        current_issue           TEXT,
        recommendation          TEXT,
        instructions            TEXT,
        allowed_actions         TEXT,
        forbidden_actions       TEXT,
        requires_human_approval INTEGER DEFAULT 1,
        schedule                TEXT DEFAULT 'manual',
        settings_json           TEXT DEFAULT '{}',
        created_at              TEXT DEFAULT (datetime('now')),
        updated_at              TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS search_missions (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        name                TEXT NOT NULL,
        description         TEXT,
        target_role         TEXT,
        target_language     TEXT DEFAULT 'Dutch',
        target_market       TEXT DEFAULT 'Netherlands',
        keywords            TEXT,
        negative_keywords   TEXT,
        allowed_sources     TEXT,
        forbidden_sources   TEXT,
        daily_target        INTEGER DEFAULT 5,
        quality_threshold   INTEGER DEFAULT 60,
        status              TEXT DEFAULT 'active',
        instructions        TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS agent_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id        INTEGER REFERENCES agents(id) ON DELETE CASCADE,
        event_type      TEXT DEFAULT 'run',
        output          TEXT,
        issue           TEXT,
        recommendation  TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS observer_recommendations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        bottleneck      TEXT,
        impact          TEXT,
        recommendation  TEXT,
        exact_fix       TEXT,
        status          TEXT DEFAULT 'open',
        related_tasks   TEXT,
        resolved_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()

    # Seed agents
    if conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 0:
        for a in _DEFAULT_AGENTS:
            conn.execute(
                """INSERT INTO agents (name, type, description, instructions,
                   allowed_actions, forbidden_actions, requires_human_approval, schedule)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (a['name'], a['type'], a['description'], a['instructions'],
                 _DEFAULT_ALLOWED, _DEFAULT_FORBIDDEN,
                 a['requires_human_approval'], a['schedule'])
            )
        conn.commit()

    # Seed missions
    if conn.execute("SELECT COUNT(*) FROM search_missions").fetchone()[0] == 0:
        for m in _DEFAULT_MISSIONS:
            fields = ['name','description','target_role','target_language','target_market',
                      'keywords','negative_keywords','allowed_sources','forbidden_sources',
                      'daily_target','quality_threshold','status','instructions']
            vals = [m.get(f,'') for f in fields]
            ph = ','.join(['?']*len(fields))
            conn.execute(f"INSERT INTO search_missions ({','.join(fields)}) VALUES ({ph})", vals)
        conn.commit()

    conn.close()


# ── Agents CRUD ───────────────────────────────────────────────────────────────

def get_agents(enabled_only=False):
    conn = get_db()
    q = "SELECT * FROM agents"
    if enabled_only:
        q += " WHERE enabled=1"
    q += " ORDER BY id"
    rows = to_list(conn.execute(q).fetchall())
    conn.close()
    return rows


def get_agent(aid):
    conn = get_db()
    row = to_dict(conn.execute("SELECT * FROM agents WHERE id=?", (aid,)).fetchone())
    conn.close()
    return row


def create_agent(data):
    conn = get_db()
    fields = ['name','type','description','instructions','allowed_actions','forbidden_actions',
              'requires_human_approval','schedule','settings_json','enabled']
    vals = [data.get(f, '') for f in fields]
    ph = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO agents ({','.join(fields)}) VALUES ({ph})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_agent(aid, data):
    conn = get_db()
    fields = ['name','type','description','instructions','allowed_actions','forbidden_actions',
              'requires_human_approval','schedule','settings_json','enabled']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), aid]
    conn.execute(f"UPDATE agents SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def toggle_agent(aid):
    conn = get_db()
    conn.execute("UPDATE agents SET enabled=CASE WHEN enabled=1 THEN 0 ELSE 1 END, updated_at=? WHERE id=?",
                 (now(), aid))
    conn.commit()
    conn.close()


# ── Agent Logs ────────────────────────────────────────────────────────────────

def get_agent_logs(agent_id, limit=20):
    conn = get_db()
    rows = to_list(conn.execute(
        "SELECT * FROM agent_logs WHERE agent_id=? ORDER BY created_at DESC LIMIT ?",
        (agent_id, limit)).fetchall())
    conn.close()
    return rows


def create_agent_log(data):
    conn = get_db()
    conn.execute(
        "INSERT INTO agent_logs (agent_id, event_type, output, issue, recommendation) VALUES (?,?,?,?,?)",
        (data.get('agent_id'), data.get('event_type','run'),
         data.get('output',''), data.get('issue',''), data.get('recommendation',''))
    )
    conn.commit()
    conn.close()


# ── Run Agent ─────────────────────────────────────────────────────────────────

def run_agent(agent_id: int):
    """Execute an agent's rule-based analysis. Returns (output, error)."""
    agent = get_agent(agent_id)
    if not agent:
        return None, "Agent not found"
    if not agent.get('enabled'):
        return None, "Agent is disabled"

    atype = agent.get('type', '')
    output = issue = recommendation = ''
    conn = get_db()

    try:
        if atype == 'candidate_research':
            try:
                rs = get_research_summary_ext()
            except Exception:
                rs = get_research_summary()
                rs.setdefault('sources_needs_fetch', 0)
                rs.setdefault('sources_blocked', 0)
                rs.setdefault('needs_enrichment', 0)
                rs.setdefault('enrichment_blocked', 0)
                rs.setdefault('enriched', 0)
                rs.setdefault('high_confidence', 0)
                rs.setdefault('medium_confidence', 0)
            missions = to_list(conn.execute(
                "SELECT * FROM search_missions WHERE status='active'").fetchall())
            total_cands = conn.execute(
                "SELECT COUNT(*) FROM cold_caller_candidates").fetchone()[0]

            output = "Candidate Research Worker — Status\n\n"
            output += f"Active missions:         {rs['active_missions']}\n"
            output += f"Sources in inbox:        {rs['total_sources']} ({rs['unprocessed']} unprocessed)\n"
            output += f"  • Needs fetch:         {rs.get('sources_needs_fetch', 0)}\n"
            output += f"  • Blocked/Manual:      {rs.get('sources_blocked', 0)}\n"
            output += f"Review queue:            {rs['queue_total']} total\n"
            output += f"  • New:                 {rs['queue_new']}\n"
            output += f"  • Needs Review:        {rs['queue_needs_review']}\n"
            output += f"  • Approved:            {rs['queue_approved']}\n"
            output += f"  • Moved→Candidates:    {rs['moved_to_candidates']}\n"
            output += f"  • Rejected/Dupes:      {rs['queue_rejected'] + rs['queue_duplicate']}\n"
            output += f"Enrichment:              {rs.get('enriched', 0)} enriched | {rs.get('needs_enrichment', 0)} pending | {rs.get('enrichment_blocked', 0)} blocked\n"
            output += f"Confidence:              {rs.get('high_confidence', 0)} high | {rs.get('medium_confidence', 0)} medium\n"
            output += f"Pipeline candidates:     {total_cands}\n\n"

            if missions:
                output += "Active search missions:\n"
                for m in missions:
                    kws = [k.strip() for k in (m.get('keywords') or '').split('\n') if k.strip()][:2]
                    output += f"▸ {m['name']} — {m.get('target_role') or 'any role'}, {m.get('target_market','NL')}, {m['daily_target']}/day target\n"
                    if kws:
                        q_str = '" OR "'.join(kws)
                        output += f'  Next query: site:linkedin.com/in ("{q_str}") "Dutch"\n'
                output += "\n"

            if rs['top_candidate']:
                tc = rs['top_candidate']
                conf = tc.get('confidence_score') or 'Low'
                output += f"Top candidate: {tc['name']} — score {tc['score']} ({tc['level']}) — {tc['best_role']} — confidence: {conf}\n"

            # Prioritised issue/recommendation
            if rs.get('sources_blocked', 0) > 0:
                issue = f"{rs['sources_blocked']} source(s) blocked or need manual review"
                recommendation = "Go to /research/sources — open blocked sources and paste the content manually"
            elif rs['unprocessed'] > 0:
                issue = f"{rs['unprocessed']} source(s) waiting to be processed"
                recommendation = "Go to /research/sources and click 'Process' on each unprocessed source"
            elif rs.get('needs_enrichment', 0) > 0:
                issue = f"{rs['needs_enrichment']} queue item(s) not yet enriched"
                recommendation = "Go to /research/queue and click 'Enrich Public Data' on unenriched items"
            elif rs['queue_needs_review'] > 0:
                issue = f"{rs['queue_needs_review']} candidate(s) need manual review"
                recommendation = "Go to /research/queue?status=Needs+Review and review each blocked candidate"
            elif rs['queue_new'] > 0:
                issue = f"{rs['queue_new']} candidates in queue waiting for review"
                recommendation = "Go to /research/queue and approve or reject candidates"
            elif not missions:
                issue = "No active search missions"
                recommendation = "Create a search mission at /search-missions/new"
            else:
                issue = ""
                recommendation = "Add a URL source at /research/url or paste results at /research/sources/new"

        elif atype == 'talent_scout':
            rows = to_list(conn.execute(
                "SELECT id, status, full_name, global_score FROM cold_caller_candidates").fetchall())
            by_status = {}
            for r in rows:
                s = r.get('status', 'found')
                by_status[s] = by_status.get(s, 0) + 1
            total = len(rows)
            if total == 0:
                issue = "No candidates in pipeline"
                output = "No candidates found. Add candidates via search missions or manually."
                recommendation = "Add candidates before scouting."
            else:
                output = f"Candidate pipeline — {total} total:\n"
                for s, n_count in sorted(by_status.items()):
                    output += f"  {s}: {n_count}\n"
                actions = []
                found_n = by_status.get('found', 0)
                qualified_n = by_status.get('qualified', 0)
                replied_n = by_status.get('replied', 0)
                if found_n:
                    actions.append(f"Review {found_n} 'found' candidate(s) — contact, reject, or AI-score them")
                if qualified_n:
                    actions.append(f"Schedule outreach or interview for {qualified_n} qualified candidate(s)")
                if replied_n:
                    actions.append(f"Follow up with {replied_n} 'replied' candidate(s)")
                if actions:
                    output += "\nActions needed:\n" + "\n".join(f"  ▸ {a}" for a in actions)
                    recommendation = actions[0]

        elif atype == 'follow_up':
            from datetime import datetime as _dtf
            today_str = _dtf.utcnow().strftime('%Y-%m-%d')
            # Action Queue overdue tasks
            overdue_tasks = to_list(conn.execute(
                """SELECT id, title, priority, task_type, related_name
                   FROM (
                     SELECT at.id, at.title, at.priority, at.task_type,
                            CASE at.related_type
                              WHEN 'candidate' THEN (SELECT full_name FROM cold_caller_candidates WHERE id=at.related_id)
                              ELSE NULL
                            END as related_name
                     FROM action_tasks at
                     WHERE at.due_date < ? AND at.status NOT IN ('Completed','Rejected')
                   ) ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
                   LIMIT 10""", (today_str,)).fetchall())
            due_today_tasks = to_list(conn.execute(
                """SELECT id, title, priority, task_type FROM action_tasks
                   WHERE due_date=? AND status NOT IN ('Completed','Rejected')
                   LIMIT 10""", (today_str,)).fetchall())
            # Outreach overdue
            due_outreach = conn.execute(
                """SELECT COUNT(*) FROM outreach_queue
                   WHERE outreach_status NOT IN ('closed','booked')
                     AND (next_follow_up_date <= ? OR next_follow_up_date IS NULL OR next_follow_up_date='')""",
                (today_str,)).fetchone()[0]
            interviews_today = to_list(conn.execute(
                """SELECT iq.interview_time, ca.full_name
                   FROM interview_queue iq
                   LEFT JOIN cold_caller_candidates ca ON iq.candidate_id=ca.id
                   WHERE iq.interview_date=? AND iq.status='scheduled'""", (today_str,)).fetchall())

            output = f"Follow-up Agent — {today_str}\n\n"
            output += f"Action Queue: {len(overdue_tasks)} overdue | {len(due_today_tasks)} due today\n"
            output += f"Outreach overdue: {due_outreach}\n"
            output += f"Interviews today: {len(interviews_today)}\n\n"
            if overdue_tasks:
                output += "Overdue tasks (top priority):\n"
                for t in overdue_tasks[:5]:
                    rn = t.get('related_name') or ''
                    output += f"  ▸ [{t['priority']}] {t['title']}" + (f" — {rn}" if rn else "") + "\n"
                issue = f"{len(overdue_tasks)} overdue action task(s)"
                recommendation = f"Open /tasks and action the {len(overdue_tasks)} overdue item(s)"
            elif due_today_tasks:
                output += "Due today:\n"
                for t in due_today_tasks[:5]:
                    output += f"  ▸ [{t['priority']}] {t['title']}\n"
                issue = ""
                recommendation = "Complete today's action tasks at /tasks"
            elif due_outreach > 0:
                issue = f"{due_outreach} overdue outreach follow-up(s)"
                recommendation = "Go to /outreach and send follow-up messages"
            else:
                issue = ""
                recommendation = "No overdue items — keep sourcing and stay consistent"
            if interviews_today:
                output += "\nInterviews today:\n"
                for i in interviews_today:
                    output += f"  ▸ {i.get('full_name','?')} at {i.get('interview_time','TBD')}\n"

        elif atype == 'performance':
            def _n(q):
                return conn.execute(q).fetchone()[0]
            cands = _n("SELECT COUNT(*) FROM cold_caller_candidates")
            active_c = _n("SELECT COUNT(*) FROM client_campaigns WHERE status='active'")
            total_c = _n("SELECT COUNT(*) FROM client_campaigns")
            placed = _n("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='placed'")
            in_interview = _n("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='interview'")
            qualified = _n("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='qualified'")
            out_total = _n("SELECT COUNT(*) FROM outreach_queue")
            out_sent = _n("SELECT COUNT(*) FROM outreach_queue WHERE outreach_status='sent'")
            out_replied = _n("SELECT COUNT(*) FROM outreach_queue WHERE outreach_status='replied'")
            int_sched = _n("SELECT COUNT(*) FROM interview_queue WHERE status='scheduled'")
            output = (
                f"Performance Summary\n\n"
                f"Campaigns:   {active_c} active / {total_c} total\n"
                f"Candidates:  {cands} total | {qualified} qualified | "
                f"{in_interview} in interview | {placed} placed\n"
                f"Outreach:    {out_total} total | {out_sent} sent | {out_replied} replied\n"
                f"Interviews:  {int_sched} scheduled\n"
            )
            if cands == 0:
                issue = "No candidates in pipeline"
                recommendation = "Start sourcing candidates immediately"
            elif placed == 0 and cands > 3:
                recommendation = "No placements yet — move qualified candidates to interview stage"
            else:
                recommendation = "Keep sourcing and convert interviewed candidates to placed"

        elif atype == 'observer':
            def _n(q):
                return conn.execute(q).fetchone()[0]
            nc = _n("SELECT COUNT(*) FROM cold_caller_candidates")
            ncamp = _n("SELECT COUNT(*) FROM client_campaigns WHERE status='active'")
            nmiss = _n("SELECT COUNT(*) FROM search_missions WHERE status='active'")
            nout = _n("SELECT COUNT(*) FROM outreach_queue WHERE outreach_status='pending'")
            nint = _n("SELECT COUNT(*) FROM interview_queue WHERE status='scheduled'")
            ndue = _n(
                "SELECT COUNT(*) FROM outreach_queue "
                "WHERE outreach_status NOT IN ('closed','booked') "
                "AND (next_follow_up_date <= date('now') OR next_follow_up_date IS NULL "
                "OR next_follow_up_date='')")

            # Also check action tasks
            noverdue_tasks = conn.execute(
                "SELECT COUNT(*) FROM action_tasks WHERE due_date < date('now') AND status NOT IN ('Completed','Rejected')"
            ).fetchone()[0] if _table_exists(conn, 'action_tasks') else 0
            napproved_stuck = conn.execute(
                "SELECT COUNT(*) FROM candidate_research_queue WHERE status='Approved'"
            ).fetchone()[0] if _table_exists(conn, 'candidate_research_queue') else 0
            nno_action = conn.execute(
                "SELECT COUNT(*) FROM cold_caller_candidates c WHERE c.status='found' AND NOT EXISTS (SELECT 1 FROM action_tasks WHERE related_type='candidate' AND related_id=c.id AND status NOT IN ('Completed','Rejected'))"
            ).fetchone()[0] if _table_exists(conn, 'action_tasks') else 0

            if nc == 0:
                bot, impact = "No candidates in pipeline", "Critical"
                rec = "Add at least 5 candidates before any other work"
                fix = "Go to /research and paste source text to find candidates"
            elif noverdue_tasks > 0:
                bot = f"{noverdue_tasks} overdue action task(s)"
                impact = "High"
                rec = f"Action {noverdue_tasks} overdue task(s) before candidates go cold"
                fix = "Go to /tasks and complete overdue items"
            elif napproved_stuck > 0:
                bot = f"{napproved_stuck} approved research candidate(s) not moved to pipeline"
                impact = "High"
                rec = "Move approved research candidates to the main pipeline"
                fix = "Go to /research/queue?status=Approved and move each candidate"
            elif nno_action > 0:
                bot = f"{nno_action} pipeline candidate(s) with no pending action task"
                impact = "Medium"
                rec = "Create screening tasks for candidates without any follow-up planned"
                fix = "Go to /tasks and create a screening task for each new candidate"
            elif ncamp == 0:
                bot, impact = "No active campaigns", "High"
                rec = "Create a campaign to enable candidate matching"
                fix = "Go to /campaigns/new and create a campaign"
            elif nmiss == 0:
                bot, impact = "No active search missions", "Medium"
                rec = "Create a search mission to direct the Candidate Research Worker"
                fix = "Go to /search-missions/new"
            elif ndue > 0:
                bot = f"{ndue} overdue outreach follow-up(s)"
                impact = "Medium"
                rec = f"Send follow-up messages to {ndue} overdue candidate(s)"
                fix = "Go to /outreach and follow up with overdue items"
            elif nout == 0 and nc > 0:
                bot, impact = "No outreach initiated", "Medium"
                rec = "Start outreach on your top candidates"
                fix = "Go to /candidates → pick top scored → Add Outreach"
            elif nint == 0 and nc > 2:
                bot, impact = "No interviews scheduled", "Low"
                rec = "Schedule an interview with your most qualified candidate"
                fix = "Go to /interviews/new"
            else:
                bot, impact = "No critical bottleneck detected", "Low"
                rec = "Pipeline is healthy — focus on sourcing velocity"
                fix = "Run Candidate Research Worker for new search queries"

            output = (
                f"Observer Analysis\n\n"
                f"  Candidates: {nc} | Active campaigns: {ncamp} | Missions: {nmiss}\n"
                f"  Pending outreach: {nout} | Interviews: {nint} | Overdue: {ndue}\n\n"
                f"Bottleneck: {bot}\n"
                f"Impact: {impact}\n"
                f"Recommendation: {rec}\n"
                f"How to fix: {fix}"
            )
            issue = bot
            recommendation = rec
            conn.close()
            conn = None
            create_observer_recommendation({
                'bottleneck': bot, 'impact': impact,
                'recommendation': rec, 'exact_fix': fix, 'status': 'open',
            })

        else:
            output = (f"Agent '{agent['name']}' checked in. "
                      f"No specific analysis configured for type '{atype}' yet.")
            recommendation = "Configure this agent's run behavior or use it manually."

    except Exception as e:
        output = f"Error during agent run: {e}"
        issue = str(e)
    finally:
        if conn is not None:
            conn.close()

    # Persist results
    uconn = get_db()
    uconn.execute(
        "UPDATE agents SET last_run_at=?, latest_output=?, current_issue=?, "
        "recommendation=?, updated_at=? WHERE id=?",
        (now(), output, issue, recommendation, now(), agent_id)
    )
    uconn.commit()
    uconn.close()

    create_agent_log({'agent_id': agent_id, 'event_type': 'run',
                      'output': output, 'issue': issue, 'recommendation': recommendation})
    return output, None


# ── Search Missions CRUD ──────────────────────────────────────────────────────

def get_search_missions(status=''):
    conn = get_db()
    q = "SELECT * FROM search_missions WHERE 1=1"
    args = []
    if status:
        q += " AND status=?"
        args.append(status)
    q += " ORDER BY created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_search_mission(mid):
    conn = get_db()
    row = to_dict(conn.execute("SELECT * FROM search_missions WHERE id=?", (mid,)).fetchone())
    conn.close()
    return row


def create_search_mission(data):
    conn = get_db()
    fields = ['name','description','target_role','target_language','target_market',
              'keywords','negative_keywords','allowed_sources','forbidden_sources',
              'daily_target','quality_threshold','status','instructions']
    vals = [data.get(f, '') for f in fields]
    ph = ','.join(['?']*len(fields))
    c = conn.execute(f"INSERT INTO search_missions ({','.join(fields)}) VALUES ({ph})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def update_search_mission(mid, data):
    conn = get_db()
    fields = ['name','description','target_role','target_language','target_market',
              'keywords','negative_keywords','allowed_sources','forbidden_sources',
              'daily_target','quality_threshold','status','instructions']
    sets = ', '.join(f"{f}=?" for f in fields) + ", updated_at=?"
    vals = [data.get(f, '') for f in fields] + [now(), mid]
    conn.execute(f"UPDATE search_missions SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def pause_search_mission(mid):
    conn = get_db()
    conn.execute(
        "UPDATE search_missions SET status=CASE WHEN status='active' THEN 'paused' ELSE 'active' END, "
        "updated_at=? WHERE id=?", (now(), mid))
    conn.commit()
    conn.close()


# ── Observer Recommendations ──────────────────────────────────────────────────

def get_observer_recommendations(status=''):
    conn = get_db()
    q = "SELECT * FROM observer_recommendations WHERE 1=1"
    args = []
    if status:
        q += " AND status=?"
        args.append(status)
    q += " ORDER BY created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def create_observer_recommendation(data):
    conn = get_db()
    conn.execute(
        "INSERT INTO observer_recommendations "
        "(bottleneck, impact, recommendation, exact_fix, status, related_tasks) "
        "VALUES (?,?,?,?,?,?)",
        (data.get('bottleneck',''), data.get('impact',''),
         data.get('recommendation',''), data.get('exact_fix',''),
         data.get('status','open'), data.get('related_tasks',''))
    )
    conn.commit()
    conn.close()


def update_observer_recommendation(rid, data):
    conn = get_db()
    status = data.get('status', 'open')
    resolved_at = datetime.utcnow().isoformat() if status == 'resolved' else None
    conn.execute(
        "UPDATE observer_recommendations SET status=?, resolved_at=? WHERE id=?",
        (status, resolved_at, rid)
    )
    conn.commit()
    conn.close()
    return rid


# ──────────────────────────────────────────────────────────────────────────────
# Research Worker — Candidate Sources + Research Queue
# ──────────────────────────────────────────────────────────────────────────────

import re as _re

def init_research_tables():
    """Create research tables. Idempotent."""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS candidate_sources (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type         TEXT NOT NULL DEFAULT 'manual_paste',
        source_name         TEXT,
        search_mission_id   INTEGER,
        raw_text            TEXT,
        source_url          TEXT,
        processed           INTEGER DEFAULT 0,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS candidate_research_queue (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        search_mission_id   INTEGER,
        candidate_source_id INTEGER,
        name                TEXT NOT NULL DEFAULT 'Unknown Candidate',
        possible_profile_url TEXT,
        source              TEXT,
        source_url          TEXT,
        snippet             TEXT,
        detected_role       TEXT,
        detected_language   TEXT,
        detected_keywords   TEXT,
        score               INTEGER DEFAULT 0,
        level               TEXT DEFAULT 'C',
        best_role           TEXT,
        best_offer_type     TEXT,
        reason              TEXT,
        risk                TEXT,
        next_action         TEXT,
        status              TEXT DEFAULT 'New',
        notes               TEXT,
        linked_candidate_id INTEGER,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()


# ── SCORING ────────────────────────────────────────────────────────────────────

_ROLE_KEYWORDS = [
    'cold call', 'cold caller', 'cold calling',
    'appointment setter', 'appointment setting',
    'sdr', 'sales development', 'outbound sales', 'outbound',
    'closer', 'high ticket', 'high-ticket',
    'b2b sales', 'b2b', 'telesales', 'telemarketing',
    'inside sales', 'business development',
]
_DUTCH_SIGNALS = [
    'dutch', 'dutch-speaking', 'dutch speaking',
    'nederland', 'netherlands', 'amsterdam', 'rotterdam', 'utrecht',
    'den haag', 'eindhoven', 'nlisch', 'nl ',
    'nederlander', 'nederlandstalig', 'moedertaal',
]
_NEGATIVE_SIGNALS = [
    'retail', 'horeca', 'waiter', 'waitress', 'bartender', 'cashier',
    'crypto', 'mlm', 'network marketing', 'pyramid',
]
_REMOTE_SIGNALS = ['remote', 'thuiswerk', 'vanuit huis', 'werk op afstand', 'flexible']
_COMMISSION_SIGNALS = ['commission', 'commissie', 'high ticket', 'high-ticket', 'closing']
_B2B_SIGNALS = ['b2b', 'business to business', 'zakelijk', 'bedrijven']
_ACTIVITY_SIGNALS = ['2024', '2025', '2026', 'recent', 'current', 'huidig', 'nu ']

def score_research_candidate(data: dict) -> dict:
    """Rule-based scoring. Returns score/level/role/offer/reason/risk/next_action."""
    text = ' '.join([
        (data.get('name') or ''),
        (data.get('snippet') or ''),
        (data.get('detected_role') or ''),
        (data.get('detected_keywords') or ''),
    ]).lower()

    score = 0
    reasons = []
    risks = []

    # Positives
    cold_calling = any(k in text for k in ['cold call', 'cold caller', 'cold calling'])
    appt_setting = any(k in text for k in ['appointment setter', 'appointment setting', 'sdr', 'sales development', 'outbound'])
    is_dutch = any(k in text for k in _DUTCH_SIGNALS)
    is_b2b = any(k in text for k in _B2B_SIGNALS)
    is_remote = any(k in text for k in _REMOTE_SIGNALS)
    is_commission = any(k in text for k in _COMMISSION_SIGNALS)
    has_recent = any(k in text for k in _ACTIVITY_SIGNALS)
    has_role = any(k in text for k in _ROLE_KEYWORDS)

    if cold_calling:
        score += 25; reasons.append('cold calling experience')
    if appt_setting:
        score += 20; reasons.append('appointment setting / SDR / outbound')
    if is_dutch:
        score += 20; reasons.append('Dutch / Nederlands signal')
    if is_b2b:
        score += 15; reasons.append('B2B experience')
    if is_remote:
        score += 15; reasons.append('remote availability')
    if is_commission:
        score += 10; reasons.append('commission / high-ticket / closing signal')
    if has_recent:
        score += 10; reasons.append('recent activity signal')

    # Negatives
    no_sales = not has_role
    retail_only = any(k in text for k in ['retail', 'horeca', 'waiter', 'waitress', 'cashier', 'bartender'])
    no_location = not is_dutch
    crypto_mlm = any(k in text for k in ['crypto', 'mlm', 'network marketing', 'pyramid'])
    vague_jobseeker = 'looking for' in text and not has_role

    if no_sales:
        score -= 30; risks.append('no sales experience detected')
    elif retail_only:
        score -= 20; risks.append('only retail / horeca sales')
    if no_location:
        score -= 20; risks.append('no Dutch / NL location match')
    if crypto_mlm:
        score -= 20; risks.append('crypto / MLM / network marketing signal')
    if vague_jobseeker:
        score -= 15; risks.append('jobseeker with no sales proof')

    score = max(0, min(100, score))

    # Level
    if score >= 65:
        level = 'A'
    elif score >= 40:
        level = 'B'
    elif score >= 20:
        level = 'C'
    else:
        level = 'Reject'

    # Best role
    if cold_calling:
        best_role = 'Cold Caller'
    elif appt_setting:
        best_role = 'Appointment Setter'
    elif is_commission:
        best_role = 'Closer'
    elif has_role:
        best_role = 'SDR / Outbound'
    else:
        best_role = 'Unclear'

    # Offer type
    if is_commission:
        best_offer_type = 'Commission / Revenue Share'
    elif is_remote:
        best_offer_type = 'Remote Freelance'
    else:
        best_offer_type = 'TBD — needs review'

    # Next action
    if level in ('A', 'B'):
        next_action = 'Approve → move to candidates → prepare outreach message'
    elif level == 'C':
        next_action = 'Review manually — low-signal profile'
    else:
        next_action = 'Reject or archive'

    return {
        'score': score,
        'level': level,
        'best_role': best_role,
        'best_offer_type': best_offer_type,
        'reason': ', '.join(reasons) if reasons else 'No strong signals found',
        'risk': ', '.join(risks) if risks else 'No major risks',
        'next_action': next_action,
    }


# ── EXTRACTION ─────────────────────────────────────────────────────────────────

_LI_URL_RE = _re.compile(r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?', _re.IGNORECASE)
_NAME_LINE_RE = _re.compile(r'^([A-Z][a-zÀ-ÿ\-]+(?:\s+[A-Z][a-zÀ-ÿ\-]+){1,3})\s*$', _re.MULTILINE)
_ROLE_RE = _re.compile(
    r'(cold call(?:er|ing)?|appointment set(?:ter|ting)|sdr|outbound sales?|'
    r'b2b sales?|telesales?|sales development|closer|high.ticket|inside sales)',
    _re.IGNORECASE
)
_DUTCH_RE = _re.compile(r'(dutch|nederland|netherlands|amsterdam|rotterdam|utrecht|'
                         r'den haag|eindhoven|nederlandstalig|nederlander|nl\b)', _re.IGNORECASE)

def _extract_linkedin_blocks(text: str) -> list:
    """Split text into candidate blocks around LinkedIn URLs or name headings."""
    blocks = []
    # Split by double-newline or by LinkedIn URL boundaries
    chunks = _re.split(r'\n{2,}', text.strip())
    for chunk in chunks:
        if chunk.strip():
            blocks.append(chunk.strip())
    return blocks

def extract_candidates_from_source(source_id: int) -> list:
    """
    Parse raw_text from a candidate_source, extract candidate signals,
    score them, dedupe, and insert into candidate_research_queue.
    Returns list of created queue item ids.
    """
    source = get_candidate_source(source_id)
    if not source:
        return []

    raw = source.get('raw_text', '') or ''
    mission_id = source.get('search_mission_id')
    source_url = source.get('source_url', '') or ''
    source_name = source.get('source_name', '') or source.get('source_type', 'paste')

    # Find all LinkedIn URLs in the text
    li_urls = list(dict.fromkeys(_LI_URL_RE.findall(raw)))  # dedupe, preserve order

    created_ids = []
    seen_urls = set()
    seen_names = set()

    def _process_block(block, li_url=None):
        nonlocal created_ids

        # Detect role keywords
        role_matches = _ROLE_RE.findall(block)
        detected_role = ', '.join(dict.fromkeys(m.lower() for m in role_matches)) if role_matches else ''

        # Detect Dutch signals
        dutch_matches = _DUTCH_RE.findall(block)
        detected_language = 'Dutch / NL' if dutch_matches else ''

        # Collect all unique keyword signals
        kw_set = set(m.lower() for m in role_matches) | set(m.lower() for m in dutch_matches)
        detected_keywords = ', '.join(sorted(kw_set))

        # Try to find a name — first line that looks like a proper name
        name = 'Unknown Candidate'
        for line in block.splitlines():
            line = line.strip()
            if _re.match(r'^[A-Z][a-zÀ-ÿ\-]+(\s+[A-Z][a-zÀ-ÿ\-]+){1,3}$', line):
                name = line
                break

        # Use LinkedIn URL from the block if not passed in
        if not li_url:
            url_in_block = _LI_URL_RE.search(block)
            li_url = url_in_block.group(0) if url_in_block else ''

        # Snippet: first 300 chars of block
        snippet = block[:300].replace('\n', ' ')

        # Dedupe
        norm_name = _re.sub(r'\s+', ' ', name.lower().strip())
        norm_url  = (li_url or '').rstrip('/').lower()

        existing = dedupe_research_candidate(name=norm_name, profile_url=norm_url)
        if existing:
            return  # duplicate — skip

        if norm_url and norm_url in seen_urls:
            return
        if norm_name != 'unknown candidate' and norm_name in seen_names:
            return
        if norm_url:
            seen_urls.add(norm_url)
        if norm_name != 'unknown candidate':
            seen_names.add(norm_name)

        candidate_data = {
            'name': name,
            'possible_profile_url': li_url,
            'snippet': snippet,
            'detected_role': detected_role,
            'detected_language': detected_language,
            'detected_keywords': detected_keywords,
        }
        scored = score_research_candidate(candidate_data)

        item = {
            'search_mission_id': mission_id,
            'candidate_source_id': source_id,
            'name': name,
            'possible_profile_url': li_url,
            'source': source_name,
            'source_url': source_url,
            'snippet': snippet,
            'detected_role': detected_role,
            'detected_language': detected_language,
            'detected_keywords': detected_keywords,
            'status': 'New',
            **scored,
        }
        qid = create_research_queue_item(item)
        created_ids.append(qid)

    # Strategy 1: if there are LinkedIn URLs, each URL anchors a block
    if li_urls:
        for url in li_urls:
            # Find the text around the URL (100 chars before, 500 after)
            idx = raw.find(url)
            if idx == -1:
                continue
            context_start = max(0, idx - 150)
            context_end   = min(len(raw), idx + 600)
            block = raw[context_start:context_end]
            _process_block(block, li_url=url)
    else:
        # Strategy 2: split into blocks and process each
        blocks = _extract_linkedin_blocks(raw)
        for block in blocks:
            if len(block.strip()) < 20:
                continue
            _process_block(block)

    # If nothing extracted but raw_text is non-empty, store as single unknown
    if not created_ids and raw.strip():
        _process_block(raw[:800])

    # Mark source as processed
    update_candidate_source(source_id, {'processed': 1})
    return created_ids


# ── CANDIDATE SOURCES CRUD ─────────────────────────────────────────────────────

def create_candidate_source(data: dict) -> int:
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO candidate_sources
           (source_type, source_name, search_mission_id, raw_text, source_url, processed)
           VALUES (?,?,?,?,?,?)""",
        (data.get('source_type', 'manual_paste'),
         data.get('source_name', ''),
         data.get('search_mission_id'),
         data.get('raw_text', ''),
         data.get('source_url', ''),
         0)
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_candidate_sources(mission_id=None, processed=None) -> list:
    conn = get_db()
    q = "SELECT cs.*, sm.name as mission_name FROM candidate_sources cs LEFT JOIN search_missions sm ON cs.search_mission_id=sm.id WHERE 1=1"
    args = []
    if mission_id is not None:
        q += " AND cs.search_mission_id=?"
        args.append(mission_id)
    if processed is not None:
        q += " AND cs.processed=?"
        args.append(processed)
    q += " ORDER BY cs.created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_candidate_source(sid: int) -> dict:
    conn = get_db()
    row = conn.execute(
        "SELECT cs.*, sm.name as mission_name FROM candidate_sources cs LEFT JOIN search_missions sm ON cs.search_mission_id=sm.id WHERE cs.id=?",
        (sid,)
    ).fetchone()
    conn.close()
    return to_dict(row)


def update_candidate_source(sid: int, data: dict):
    conn = get_db()
    fields = ['source_type', 'source_name', 'search_mission_id', 'raw_text', 'source_url', 'processed']
    sets = []
    vals = []
    for f in fields:
        if f in data:
            sets.append(f"{f}=?")
            vals.append(data[f])
    if not sets:
        conn.close()
        return
    sets.append("updated_at=datetime('now')")
    vals.append(sid)
    conn.execute(f"UPDATE candidate_sources SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


# ── RESEARCH QUEUE CRUD ────────────────────────────────────────────────────────

_RQ_FIELDS = [
    'search_mission_id', 'candidate_source_id', 'name', 'possible_profile_url',
    'source', 'source_url', 'snippet', 'detected_role', 'detected_language',
    'detected_keywords', 'score', 'level', 'best_role', 'best_offer_type',
    'reason', 'risk', 'next_action', 'status', 'notes', 'linked_candidate_id',
]

def create_research_queue_item(data: dict) -> int:
    conn = get_db()
    cols = [f for f in _RQ_FIELDS if f in data]
    placeholders = ','.join('?' * len(cols))
    vals = [data[c] for c in cols]
    cur = conn.execute(
        f"INSERT INTO candidate_research_queue ({', '.join(cols)}) VALUES ({placeholders})",
        vals
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_research_queue(status=None, mission_id=None, source_id=None) -> list:
    conn = get_db()
    q = """SELECT rq.*, sm.name as mission_name
           FROM candidate_research_queue rq
           LEFT JOIN search_missions sm ON rq.search_mission_id=sm.id
           WHERE 1=1"""
    args = []
    if status:
        if isinstance(status, list):
            placeholders = ','.join('?' * len(status))
            q += f" AND rq.status IN ({placeholders})"
            args.extend(status)
        else:
            q += " AND rq.status=?"
            args.append(status)
    if mission_id is not None:
        q += " AND rq.search_mission_id=?"
        args.append(mission_id)
    if source_id is not None:
        q += " AND rq.candidate_source_id=?"
        args.append(source_id)
    q += " ORDER BY rq.score DESC, rq.created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_research_queue_item(rid: int) -> dict:
    conn = get_db()
    row = conn.execute(
        """SELECT rq.*, sm.name as mission_name
           FROM candidate_research_queue rq
           LEFT JOIN search_missions sm ON rq.search_mission_id=sm.id
           WHERE rq.id=?""",
        (rid,)
    ).fetchone()
    conn.close()
    return to_dict(row)


def update_research_queue_item(rid: int, data: dict):
    conn = get_db()
    sets = []
    vals = []
    for f in _RQ_FIELDS:
        if f in data:
            sets.append(f"{f}=?")
            vals.append(data[f])
    if not sets:
        conn.close()
        return
    sets.append("updated_at=datetime('now')")
    vals.append(rid)
    conn.execute(f"UPDATE candidate_research_queue SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def approve_research_candidate(rid: int):
    update_research_queue_item(rid, {'status': 'Approved'})
    # Auto-create "Move To Candidates" task
    try:
        item = get_research_queue_item(rid)
        if item:
            create_action_task({
                'task_type':    'move_to_candidates',
                'related_type': 'research_item',
                'related_id':   rid,
                'title':        f"Move to candidates: {item.get('name','?')}",
                'description':  f"Approved research candidate ready to move to pipeline.",
                'message':      _task_message('move_to_candidates', name=item.get('name','?')),
                'priority':     'High',
                'status':       'Pending',
                'due_date':     _today(),
            })
    except Exception:
        pass


def reject_research_candidate(rid: int):
    update_research_queue_item(rid, {'status': 'Rejected'})


def mark_research_duplicate(rid: int):
    update_research_queue_item(rid, {'status': 'Duplicate'})


def dedupe_research_candidate(name: str, profile_url: str,
                               phone: str = None, email: str = None) -> int:
    """Return existing research queue item id if duplicate, else None."""
    conn = get_db()
    # Check by profile URL first (most reliable)
    if profile_url and profile_url.strip():
        norm = profile_url.rstrip('/').lower()
        row = conn.execute(
            "SELECT id FROM candidate_research_queue WHERE lower(trim(possible_profile_url, '/'))=? LIMIT 1",
            (norm,)
        ).fetchone()
        if row:
            conn.close()
            return row[0]

    # Check by normalized name
    if name and name.lower() != 'unknown candidate':
        norm_name = _re.sub(r'\s+', ' ', name.lower().strip())
        row = conn.execute(
            "SELECT id FROM candidate_research_queue WHERE lower(trim(name))=? LIMIT 1",
            (norm_name,)
        ).fetchone()
        if row:
            conn.close()
            return row[0]

    # Also check candidates table by LinkedIn URL
    if profile_url and profile_url.strip():
        norm = profile_url.rstrip('/').lower()
        row = conn.execute(
            "SELECT id FROM cold_caller_candidates WHERE lower(trim(profile_url, '/'))=? LIMIT 1",
            (norm,)
        ).fetchone()
        if row:
            conn.close()
            return row[0]

    conn.close()
    return None


def move_research_candidate_to_candidates(rid: int) -> int:
    """
    Create a cold_caller_candidate from an approved research queue item.
    Returns the new candidate id.
    """
    item = get_research_queue_item(rid)
    if not item:
        return None

    notes_parts = []
    if item.get('reason'):
        notes_parts.append(f"Signals: {item['reason']}")
    if item.get('risk'):
        notes_parts.append(f"Risk: {item['risk']}")
    if item.get('next_action'):
        notes_parts.append(f"Next action: {item['next_action']}")
    if item.get('notes'):
        notes_parts.append(f"Notes: {item['notes']}")
    combined_notes = ' | '.join(notes_parts)

    candidate_data = {
        'full_name': item.get('name', 'Unknown'),
        'profile_url': item.get('possible_profile_url', ''),
        'platform_source': item.get('source', 'Research Worker'),
        'current_role': item.get('detected_role', ''),
        'language_level': 'Dutch' if 'dutch' in (item.get('detected_language') or '').lower() else '',
        'global_score': item.get('score', 0),
        'status': 'found',
        'notes': combined_notes,
        # email/phone not available at research stage
        'email': '',
        'phone': '',
        'past_sales_roles': item.get('best_role', ''),
        'cold_calling_experience': 'yes' if 'cold call' in (item.get('detected_role') or '').lower() else '',
        'appointment_setting_experience': 'yes' if 'appointment' in (item.get('detected_role') or '').lower() else '',
        'b2b_experience': 'yes' if 'b2b' in (item.get('detected_keywords') or '').lower() else '',
        'availability': 'remote' if item.get('best_offer_type') and 'remote' in item['best_offer_type'].lower() else '',
        'commission_only_fit': 'yes' if item.get('best_offer_type') and 'commission' in item['best_offer_type'].lower() else '',
        'proof_results': '',
        'voice_sample_url': '',
        'd2d_experience': '',
        'gatekeeper_experience': '',
        'ai_score_raw': '',
    }

    cid = create_candidate(candidate_data)
    update_research_queue_item(rid, {
        'status': 'Moved To Candidates',
        'linked_candidate_id': cid,
    })
    # Auto-create screening task for Action Queue
    try:
        create_candidate_next_action_task(cid, task_type='screening_message', priority='High')
    except Exception:
        pass
    return cid


# ── QUERY BUILDER ──────────────────────────────────────────────────────────────

def generate_search_queries(mission: dict) -> list:
    """
    Generate safe, non-automated search queries for a search mission.
    Returns list of {type, query, description} dicts.
    """
    lang = mission.get('target_language') or 'Dutch'
    market = mission.get('target_market') or 'Netherlands'
    role = mission.get('target_role') or 'Cold Caller'
    keywords_raw = mission.get('keywords') or ''
    kws = [k.strip() for k in keywords_raw.splitlines() if k.strip()]

    lang_lower = lang.lower()
    is_dutch = 'dutch' in lang_lower or 'nl' in lang_lower or 'neder' in lang_lower

    loc_terms = '"Nederland"' if is_dutch else f'"{market}"'
    lang_terms = '("Dutch" OR "Nederlands" OR "Nederlandstalig")' if is_dutch else f'"{lang}"'
    role_terms_map = {
        'cold caller':          '("cold caller" OR "cold calling" OR "cold call")',
        'appointment setter':   '("appointment setter" OR "appointment setting" OR "SDR")',
        'closer':               '("closer" OR "high ticket" OR "high-ticket closing")',
    }
    role_key = role.lower()
    role_q = next((v for k, v in role_terms_map.items() if k in role_key),
                  '("cold caller" OR "appointment setter" OR "SDR")')

    queries = []

    # 1. Google indexed LinkedIn
    queries.append({
        'type': 'google_linkedin',
        'label': 'Google → LinkedIn indexed',
        'query': f'site:linkedin.com/in {role_q} {lang_terms}',
        'description': 'Paste into Google. Results are public LinkedIn profiles indexed by Google.',
    })

    # 2. Google Alert phrase
    queries.append({
        'type': 'google_alert',
        'label': 'Google Alert phrase',
        'query': f'"{role.lower()}" "{lang_lower}" remote',
        'description': 'Set this as a Google Alert to receive new matches by email.',
    })

    # 3. LinkedIn manual search (for human to enter in LinkedIn search bar)
    queries.append({
        'type': 'linkedin_manual',
        'label': 'LinkedIn manual search (paste into LinkedIn)',
        'query': f'{role} {lang} remote',
        'description': 'Paste into LinkedIn People search bar. Filter by location: Netherlands.',
    })

    # 4. Community referral phrase
    queries.append({
        'type': 'community_referral',
        'label': 'Community / referral post',
        'query': f'Looking for a {lang}-speaking {role.lower()} with B2B experience. Remote. Commission-based. DM me.',
        'description': 'Post in relevant Facebook groups, Slack communities, WhatsApp sales groups.',
    })

    # 5. Google broad search
    queries.append({
        'type': 'google_broad',
        'label': 'Google broad search',
        'query': f'"{role.lower()}" "{market}" "remote" site:freelancer.nl OR site:upwork.com OR site:linkedin.com',
        'description': 'Broad Google search across freelance platforms.',
    })

    # 6. Custom keyword queries from the mission
    for kw in kws[:4]:
        queries.append({
            'type': 'keyword',
            'label': f'Keyword: {kw}',
            'query': f'"{kw}" {loc_terms} {lang_terms}',
            'description': f'Custom keyword query from mission: {kw}',
        })

    return queries


# ── RESEARCH AGENT SUMMARY ─────────────────────────────────────────────────────

def get_research_summary() -> dict:
    """Summary counts for the research dashboard and agent output."""
    conn = get_db()
    def _count(q, *args):
        return conn.execute(q, args).fetchone()[0]

    d = {
        'total_sources':      _count("SELECT COUNT(*) FROM candidate_sources"),
        'unprocessed':        _count("SELECT COUNT(*) FROM candidate_sources WHERE processed=0"),
        'queue_total':        _count("SELECT COUNT(*) FROM candidate_research_queue"),
        'queue_new':          _count("SELECT COUNT(*) FROM candidate_research_queue WHERE status='New'"),
        'queue_needs_review': _count("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Needs Review'"),
        'queue_approved':     _count("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Approved'"),
        'queue_rejected':     _count("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Rejected'"),
        'queue_duplicate':    _count("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Duplicate'"),
        'moved_to_candidates':_count("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Moved To Candidates'"),
        'active_missions':    _count("SELECT COUNT(*) FROM search_missions WHERE status='active'"),
    }

    # Top candidate in queue
    top = conn.execute(
        "SELECT * FROM candidate_research_queue WHERE status NOT IN ('Rejected','Duplicate') ORDER BY score DESC LIMIT 1"
    ).fetchone()
    d['top_candidate'] = to_dict(top)

    conn.close()
    return d


# ──────────────────────────────────────────────────────────────────────────────
# Action Queue + Follow-up Engine
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime as _dt, timedelta as _td

# ── MESSAGE TEMPLATES ──────────────────────────────────────────────────────────

_TASK_MESSAGES = {
    'screening_message': (
        "Yo {name}, nice dat je interesse hebt. "
        "Korte check voordat we iets plannen:\n\n"
        "1. Heb je ervaring met cold calling of appointment setting?\n"
        "2. Spreek je vloeiend Nederlands?\n"
        "3. Hoeveel uur per week kun je bellen?\n"
        "4. Ben je comfortabel met commissie?\n"
        "5. Kun je een voice note sturen van 60 sec "
        "waarin je jezelf kort verkoopt als cold caller?\n\n"
        "Laat het me weten!"
    ),
    'voice_note_request': (
        "Hey {name}, bedankt voor je reactie! "
        "Om verder te gaan zou ik graag een voice note van je willen horen — "
        "60 seconden in het Nederlands, pitch jezelf als cold caller. "
        "Gewoon relaxed, geen voorbereiding nodig. Stuur hem als je even tijd hebt!"
    ),
    'test_call_invite': (
        "Hey {name}, we'd like to do a quick 15-minute test call this week. "
        "We'll do a short cold calling simulation together. "
        "Does {date} work? If not, what days are you free this week?"
    ),
    'follow_up_1': (
        "Hey {name}, just checking in! "
        "Did you get a chance to look at my last message? "
        "We're still looking for a Dutch-speaking cold caller "
        "and you looked like a strong fit. Still interested?"
    ),
    'follow_up_2': (
        "Hey {name}, last follow-up from me! "
        "We have one spot left for a Dutch cold caller "
        "and I wanted to give you first shot. "
        "If this isn't a good time — no worries, just reply NO "
        "and I'll close your application. Otherwise reply YES and I'll send details!"
    ),
    'rejection': (
        "Hi {name}, thanks for your time and interest! "
        "After careful consideration we've decided to move forward with other candidates for now. "
        "I'll keep your profile and reach out again if a better match comes up. "
        "Best of luck!"
    ),
    'nurture': (
        "Hey {name}, how are you? "
        "We spoke a while back about a cold calling role. "
        "We have some new campaigns starting and thought of you. "
        "Available for a quick chat this week?"
    ),
    'interview_reminder': (
        "Reminder: Interview with {name} today. "
        "Review their profile and test-call criteria before the call."
    ),
    'match_to_offer': (
        "Review {name} and match them to the best active campaign. "
        "Check their score, role fit and offer type, then assign via /matches."
    ),
    'decision': (
        "Post-interview decision needed for {name}. "
        "Review notes and mark: Qualified / Rejected / Needs Another Call."
    ),
    'move_to_candidates': (
        "Research candidate {name} is approved. "
        "Move them to the main candidates pipeline via /research/queue."
    ),
}


def _task_message(task_type: str, name: str = '', date: str = '') -> str:
    tmpl = _TASK_MESSAGES.get(task_type, '')
    return tmpl.format(name=name, date=date or 'this week')


def _future_date(days: int) -> str:
    return (_dt.utcnow() + _td(days=days)).strftime('%Y-%m-%d')


def _today() -> str:
    return _dt.utcnow().strftime('%Y-%m-%d')


# ── TABLE INIT ─────────────────────────────────────────────────────────────────

def init_action_tasks_table():
    """Create action_tasks table. Idempotent."""
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS action_tasks (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type       TEXT NOT NULL DEFAULT 'general',
        related_type    TEXT,
        related_id      INTEGER,
        title           TEXT NOT NULL,
        description     TEXT,
        message         TEXT,
        priority        TEXT DEFAULT 'Medium',
        status          TEXT DEFAULT 'Pending',
        owner           TEXT,
        due_date        TEXT,
        completed_at    TEXT,
        notes           TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    # Migrate any legacy 'Open' tasks to 'Pending' (idempotent)
    conn.execute("UPDATE action_tasks SET status='Pending' WHERE status='Open'")
    conn.commit()
    conn.close()


# ── CRUD ────────────────────────────────────────────────────────────────────────

_AT_FIELDS = [
    'task_type', 'related_type', 'related_id', 'title', 'description',
    'message', 'priority', 'status', 'owner', 'due_date',
    'completed_at', 'notes',
]


def create_action_task(data: dict) -> int:
    conn = get_db()
    cols = [f for f in _AT_FIELDS if f in data]
    ph   = ','.join('?' * len(cols))
    vals = [data[c] for c in cols]
    cur  = conn.execute(
        f"INSERT INTO action_tasks ({', '.join(cols)}) VALUES ({ph})", vals
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_action_tasks(status=None, priority=None, task_type=None,
                     related_type=None, overdue_only=False,
                     due_today=False, limit=200) -> list:
    conn = get_db()
    q = """
        SELECT at.*,
               CASE at.related_type
                 WHEN 'candidate'     THEN (SELECT full_name FROM cold_caller_candidates WHERE id=at.related_id)
                 WHEN 'research_item' THEN (SELECT name FROM candidate_research_queue WHERE id=at.related_id)
                 WHEN 'outreach'      THEN (SELECT full_name FROM cold_caller_candidates c
                                            JOIN outreach_queue oq ON oq.candidate_id=c.id
                                            WHERE oq.id=at.related_id LIMIT 1)
                 WHEN 'interview'     THEN (SELECT full_name FROM cold_caller_candidates c
                                            JOIN interview_queue iq ON iq.candidate_id=c.id
                                            WHERE iq.id=at.related_id LIMIT 1)
                 ELSE NULL
               END as related_name
        FROM action_tasks at
        WHERE 1=1
    """
    args = []
    if status:
        if isinstance(status, list):
            q += f" AND at.status IN ({','.join('?'*len(status))})"
            args.extend(status)
        else:
            q += " AND at.status=?"; args.append(status)
    if priority:
        q += " AND at.priority=?"; args.append(priority)
    if task_type:
        q += " AND at.task_type=?"; args.append(task_type)
    if related_type:
        q += " AND at.related_type=?"; args.append(related_type)
    if overdue_only:
        q += " AND at.due_date < date('now') AND at.status NOT IN ('Completed','Rejected')"
    if due_today:
        q += " AND at.due_date = date('now') AND at.status NOT IN ('Completed','Rejected')"
    q += " ORDER BY CASE at.priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, at.due_date ASC LIMIT ?"
    args.append(limit)
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_action_task(tid: int) -> dict:
    conn = get_db()
    row = conn.execute("""
        SELECT at.*,
               CASE at.related_type
                 WHEN 'candidate'     THEN (SELECT full_name FROM cold_caller_candidates WHERE id=at.related_id)
                 WHEN 'research_item' THEN (SELECT name FROM candidate_research_queue WHERE id=at.related_id)
                 ELSE NULL
               END as related_name
        FROM action_tasks at WHERE at.id=?
    """, (tid,)).fetchone()
    conn.close()
    return to_dict(row)


def update_action_task(tid: int, data: dict):
    conn = get_db()
    updatable = _AT_FIELDS
    sets = [f"{f}=?" for f in updatable if f in data]
    vals = [data[f] for f in updatable if f in data]
    if not sets:
        conn.close(); return
    sets.append("updated_at=datetime('now')")
    vals.append(tid)
    conn.execute(f"UPDATE action_tasks SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def complete_action_task(tid: int):
    update_action_task(tid, {
        'status': 'Completed',
        'completed_at': _dt.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
    })


def mark_task_copied(tid: int):
    """Mark message as copied — user now has the text to send manually."""
    update_action_task(tid, {'status': 'Copied'})


def mark_task_sent(tid: int) -> int:
    """
    Mark task Sent. For outreach-type tasks, auto-create the appropriate follow-up.
    Returns follow-up task id or None.
    """
    task = get_action_task(tid)
    if not task:
        return None

    update_action_task(tid, {'status': 'Sent'})

    task_type   = task.get('task_type', '')
    related_id  = task.get('related_id')
    related_type= task.get('related_type', '')
    name        = task.get('related_name') or 'the candidate'

    follow_up_tid = None

    if task_type == 'screening_message':
        follow_up_tid = create_action_task({
            'task_type':    'follow_up_1',
            'related_type': related_type,
            'related_id':   related_id,
            'title':        f"Follow-up: {name}",
            'description':  'No response to screening message — send follow-up.',
            'message':      _task_message('follow_up_1', name=name),
            'priority':     'Medium',
            'status':       'Pending',
            'due_date':     _future_date(2),
        })

    elif task_type in ('voice_note_request', 'follow_up_1'):
        follow_up_tid = create_action_task({
            'task_type':    'follow_up_2',
            'related_type': related_type,
            'related_id':   related_id,
            'title':        f"Follow-up 2: {name}",
            'description':  'Second follow-up — last attempt before archiving.',
            'message':      _task_message('follow_up_2', name=name),
            'priority':     'Medium',
            'status':       'Pending',
            'due_date':     _future_date(2),
        })

    elif task_type == 'follow_up_2':
        # Last follow-up — create a nurture/decision task in 3 days
        follow_up_tid = create_action_task({
            'task_type':    'nurture',
            'related_type': related_type,
            'related_id':   related_id,
            'title':        f"Nurture or close: {name}",
            'description':  'No response after 2 follow-ups. Either nurture long-term or reject.',
            'message':      _task_message('nurture', name=name),
            'priority':     'Low',
            'status':       'Pending',
            'due_date':     _future_date(3),
        })

    elif task_type == 'test_call_invite':
        follow_up_tid = create_action_task({
            'task_type':    'interview_reminder',
            'related_type': related_type,
            'related_id':   related_id,
            'title':        f"Test call reminder: {name}",
            'description':  'Ensure test call happened and log outcome.',
            'message':      _task_message('interview_reminder', name=name),
            'priority':     'High',
            'status':       'Pending',
            'due_date':     _future_date(1),
        })

    return follow_up_tid


def reject_action_task(tid: int):
    update_action_task(tid, {'status': 'Rejected'})


def reschedule_action_task(tid: int, new_due_date: str, notes: str = ''):
    data = {'status': 'Rescheduled', 'due_date': new_due_date}
    if notes:
        existing = get_action_task(tid)
        old_notes = existing.get('notes') or ''
        data['notes'] = (old_notes + f"\n[Rescheduled to {new_due_date}]: {notes}").strip()
    update_action_task(tid, data)


def get_due_tasks() -> list:
    return get_action_tasks(due_today=True)


def get_overdue_tasks() -> list:
    return get_action_tasks(overdue_only=True)


# ── TASK FACTORY HELPERS ───────────────────────────────────────────────────────

def create_followup_task(related_type: str, related_id: int,
                          name: str, days: int = 2,
                          task_type: str = 'follow_up_1',
                          priority: str = 'Medium') -> int:
    return create_action_task({
        'task_type':    task_type,
        'related_type': related_type,
        'related_id':   related_id,
        'title':        f"Follow-up: {name}",
        'description':  'Scheduled follow-up.',
        'message':      _task_message(task_type, name=name),
        'priority':     priority,
        'status':       'Pending',
        'due_date':     _future_date(days),
    })


def create_candidate_next_action_task(candidate_id: int,
                                       task_type: str = 'screening_message',
                                       priority: str = 'High') -> int:
    """Create a task linked to a candidate. Looks up candidate name automatically."""
    conn = get_db()
    row  = conn.execute(
        "SELECT full_name FROM cold_caller_candidates WHERE id=?", (candidate_id,)
    ).fetchone()
    conn.close()
    name = row[0] if row else f"Candidate #{candidate_id}"

    return create_action_task({
        'task_type':    task_type,
        'related_type': 'candidate',
        'related_id':   candidate_id,
        'title':        f"{task_type.replace('_', ' ').title()}: {name}",
        'description':  f"Auto-created for {name}.",
        'message':      _task_message(task_type, name=name),
        'priority':     priority,
        'status':       'Pending',
        'due_date':     _today(),
    })


def create_client_next_action_task(campaign_id: int,
                                    task_type: str = 'match_to_offer',
                                    priority: str = 'Medium') -> int:
    conn = get_db()
    row  = conn.execute(
        "SELECT client_name FROM client_campaigns WHERE id=?", (campaign_id,)
    ).fetchone()
    conn.close()
    name = row[0] if row else f"Campaign #{campaign_id}"

    return create_action_task({
        'task_type':    task_type,
        'related_type': 'campaign',
        'related_id':   campaign_id,
        'title':        f"{task_type.replace('_', ' ').title()}: {name}",
        'description':  f"Auto-created for campaign: {name}.",
        'message':      _task_message(task_type, name=name),
        'priority':     priority,
        'status':       'Pending',
        'due_date':     _today(),
    })


def get_action_task_summary() -> dict:
    """Counts for the dashboard."""
    conn = get_db()
    def _n(q, *a):
        return conn.execute(q, a).fetchone()[0]
    today = _today()
    d = {
        'pending':       _n("SELECT COUNT(*) FROM action_tasks WHERE status='Pending'"),
        'due_today':     _n("SELECT COUNT(*) FROM action_tasks WHERE due_date=? AND status NOT IN ('Completed','Rejected')", today),
        'overdue':       _n("SELECT COUNT(*) FROM action_tasks WHERE due_date < ? AND status NOT IN ('Completed','Rejected')", today),
        'high_priority': _n("SELECT COUNT(*) FROM action_tasks WHERE priority IN ('High','Critical') AND status NOT IN ('Completed','Rejected')"),
        'sent_pending':  _n("SELECT COUNT(*) FROM action_tasks WHERE status='Sent'"),
        'completed_today': _n("SELECT COUNT(*) FROM action_tasks WHERE status='Completed' AND date(completed_at)=?", today),
        'blocked':       _n("SELECT COUNT(*) FROM action_tasks WHERE status IN ('Blocked','Needs Review')"),
        'copied':        _n("SELECT COUNT(*) FROM action_tasks WHERE status='Copied'"),
        'total':         _n("SELECT COUNT(*) FROM action_tasks"),
    }
    conn.close()
    return d


# ──────────────────────────────────────────────────────────────────────────────
# Link Research Worker
# ──────────────────────────────────────────────────────────────────────────────

import re as _lre
import urllib.request as _urllib_req
import urllib.error as _urllib_err
import urllib.parse as _urllib_parse
import html as _html_mod
from html.parser import HTMLParser as _HTMLParser

# ── MIGRATION (phase3) ─────────────────────────────────────────────────────────

def migrate_phase3():
    """Add link-research columns. Safe to call multiple times."""
    conn = get_db()
    for sql in [
        # candidate_sources
        "ALTER TABLE candidate_sources ADD COLUMN title TEXT",
        "ALTER TABLE candidate_sources ADD COLUMN source_mode TEXT DEFAULT 'Manual Paste'",
        "ALTER TABLE candidate_sources ADD COLUMN fetch_status TEXT DEFAULT 'Not Fetched'",
        "ALTER TABLE candidate_sources ADD COLUMN fetch_error TEXT",
        "ALTER TABLE candidate_sources ADD COLUMN fetched_title TEXT",
        "ALTER TABLE candidate_sources ADD COLUMN fetched_html_excerpt TEXT",
        "ALTER TABLE candidate_sources ADD COLUMN fetched_at TEXT",
        # candidate_research_queue
        "ALTER TABLE candidate_research_queue ADD COLUMN enrichment_status TEXT DEFAULT 'Not Started'",
        "ALTER TABLE candidate_research_queue ADD COLUMN enrichment_error TEXT",
        "ALTER TABLE candidate_research_queue ADD COLUMN fetched_headline TEXT",
        "ALTER TABLE candidate_research_queue ADD COLUMN fetched_location TEXT",
        "ALTER TABLE candidate_research_queue ADD COLUMN fetched_about_excerpt TEXT",
        "ALTER TABLE candidate_research_queue ADD COLUMN fetched_profile_text TEXT",
        "ALTER TABLE candidate_research_queue ADD COLUMN researched_at TEXT",
        "ALTER TABLE candidate_research_queue ADD COLUMN confidence_score TEXT DEFAULT 'Low'",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass
    conn.close()


# ── EXTENDED FIELD LISTS ───────────────────────────────────────────────────────

_CS_FIELDS_EXT = [
    'source_type', 'source_name', 'search_mission_id', 'raw_text', 'source_url',
    'processed', 'title', 'source_mode', 'fetch_status', 'fetch_error',
    'fetched_title', 'fetched_html_excerpt', 'fetched_at',
]

_RQ_FIELDS_EXT = [
    'search_mission_id', 'candidate_source_id', 'name', 'possible_profile_url',
    'source', 'source_url', 'snippet', 'detected_role', 'detected_language',
    'detected_keywords', 'score', 'level', 'best_role', 'best_offer_type',
    'reason', 'risk', 'next_action', 'status', 'notes', 'linked_candidate_id',
    'enrichment_status', 'enrichment_error', 'fetched_headline', 'fetched_location',
    'fetched_about_excerpt', 'fetched_profile_text', 'researched_at', 'confidence_score',
]


# ── HTTP FETCH ─────────────────────────────────────────────────────────────────

_FETCH_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
}

_FETCH_TIMEOUT = 10
_MAX_BYTES = 400_000   # 400 KB limit


def fetch_public_url(url: str) -> dict:
    """
    Fetch a public URL via plain HTTP. Returns:
      {ok, status_code, content_type, html, title, text_excerpt, error, blocked}

    Rules:
    - Only HTTP(S). No authentication.
    - If blocked / login-required / 403 / unusual redirect → blocked=True.
    - If any error → ok=False, error=message.
    - Respects robots: does not bypass anything; just reads public pages.
    """
    result = {
        'ok': False, 'status_code': 0, 'content_type': '',
        'html': '', 'title': '', 'text_excerpt': '', 'error': '', 'blocked': False,
    }

    if not url or not url.strip():
        result['error'] = 'Empty URL'
        return result

    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # LinkedIn always blocks unauthenticated scraping — mark immediately
    parsed = _urllib_parse.urlparse(url)
    host = parsed.netloc.lower().lstrip('www.')
    if 'linkedin.com' in host:
        result['blocked'] = True
        result['error'] = (
            'LinkedIn requires login to view profiles. '
            'Open this URL manually in your browser and paste the visible text into a Manual Paste source.'
        )
        return result

    try:
        req = _urllib_req.Request(url, headers=_FETCH_HEADERS)
        with _urllib_req.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            result['status_code'] = resp.status
            ct = resp.headers.get('Content-Type', '')
            result['content_type'] = ct

            if resp.status in (301, 302, 303, 307, 308):
                result['blocked'] = True
                result['error'] = f'Redirect (status {resp.status}) — may require login'
                return result

            raw = resp.read(_MAX_BYTES)
            try:
                html = raw.decode('utf-8', errors='replace')
            except Exception:
                html = raw.decode('latin-1', errors='replace')

            result['html'] = html
            result['ok'] = True

            # Detect login / block pages
            block_signals = [
                'sign in', 'log in', 'login required', 'create account',
                'join linkedin', 'authwall', 'checkpoint', 'access denied',
                '403 forbidden', 'rate limited', 'captcha',
            ]
            html_lower = html.lower()
            if any(s in html_lower for s in block_signals[:5]) and resp.status in (200,):
                # check title for extra confidence
                title_m = _lre.search(r'<title[^>]*>(.*?)</title>', html, _lre.IGNORECASE | _lre.DOTALL)
                t = title_m.group(1).strip() if title_m else ''
                if any(s in t.lower() for s in ['sign in', 'log in', 'login']):
                    result['blocked'] = True
                    result['error'] = (
                        'Page requires login. '
                        'Open it manually and paste the visible text into a Manual Paste source.'
                    )

            # Extract title
            title_m = _lre.search(r'<title[^>]*>(.*?)</title>', html, _lre.IGNORECASE | _lre.DOTALL)
            result['title'] = _html_mod.unescape(title_m.group(1).strip()) if title_m else ''

            # Extract plain text excerpt
            result['text_excerpt'] = _html_to_text(html)[:3000]

    except _urllib_err.HTTPError as e:
        result['status_code'] = e.code
        if e.code in (401, 403, 429):
            result['blocked'] = True
            result['error'] = f'HTTP {e.code} — access denied or rate limited'
        else:
            result['error'] = f'HTTP error {e.code}'
    except _urllib_err.URLError as e:
        result['error'] = f'URL error: {e.reason}'
    except Exception as e:
        result['error'] = f'Fetch error: {e}'

    return result


class _TextExtractor(_HTMLParser):
    """Minimal HTML → plain text converter."""
    SKIP_TAGS = {'script', 'style', 'noscript', 'head', 'meta', 'link', 'img'}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self._skip > 0:
            self._skip -= 1
        if tag.lower() in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if self._skip == 0:
            self.parts.append(data)


def _html_to_text(html: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    text = ''.join(p.parts)
    # Collapse whitespace
    text = _lre.sub(r'\n{3,}', '\n\n', text)
    text = _lre.sub(r'[ \t]+', ' ', text)
    return text.strip()


# ── HTML LINK EXTRACTION ───────────────────────────────────────────────────────

_HREF_RE = _lre.compile(r'href=["\']([^"\'>\s]+)["\']', _lre.IGNORECASE)
_LI_PROFILE_RE = _lre.compile(r'https?://(?:www\.)?linkedin\.com/in/([\w\-]+)/?', _lre.IGNORECASE)
_LI_SLUG_RE = _lre.compile(r'linkedin\.com/in/([\w\-]+)', _lre.IGNORECASE)


def extract_links_from_html(html: str, base_url: str = '') -> list:
    """Return list of absolute URL strings found in HTML href attributes."""
    links = []
    for m in _HREF_RE.finditer(html):
        href = m.group(1)
        if href.startswith('#') or href.startswith('javascript'):
            continue
        if href.startswith('http'):
            links.append(href)
        elif base_url and href.startswith('/'):
            parsed = _urllib_parse.urlparse(base_url)
            links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
    return links


def extract_linkedin_profile_urls(text_or_html: str) -> list:
    """
    Extract unique linkedin.com/in/{slug} URLs from any text/HTML.
    Returns list of full https:// URLs, deduped.
    """
    seen = {}
    for m in _LI_PROFILE_RE.finditer(text_or_html):
        slug = m.group(1).lower()
        url = f"https://www.linkedin.com/in/{slug}/"
        seen[slug] = url
    # Also catch bare slugs like 'linkedin.com/in/jandevries'
    for m in _LI_SLUG_RE.finditer(text_or_html):
        slug = m.group(1).lower()
        if slug not in seen:
            seen[slug] = f"https://www.linkedin.com/in/{slug}/"
    return list(seen.values())


# ── NAME EXTRACTION FROM TITLES ────────────────────────────────────────────────

_LI_TITLE_RE = _lre.compile(
    r'^(?:LinkedIn\s*[·•\-–|]\s*)?'       # optional "LinkedIn · "
    r'([A-Z][^\|•·\-–]{2,40}?)'           # capture: name part
    r'\s*[\|•·\-–]',                       # separator
    _lre.IGNORECASE
)
_NAME_PATTERNS = [
    # "LinkedIn · Name"
    _lre.compile(r'LinkedIn\s*[·•]\s*([A-Z][a-zÀ-ÿ\-]+(?:\s+[A-Z][a-zÀ-ÿ\-]+){1,4})', _lre.IGNORECASE),
    # "Name — Title" or "Name - Title" or "Name | Title"
    _lre.compile(r'^([A-Z][a-zÀ-ÿ\-]+(?:\s+[A-Z][a-zÀ-ÿ\-]+){1,4})\s*[—\-|]'),
]

def _name_from_title(title: str, slug: str = '') -> str:
    """Try to extract a human name from a page title. Falls back to slug."""
    t = title.strip()
    for pat in _NAME_PATTERNS:
        m = pat.search(t)
        if m:
            candidate = m.group(1).strip()
            # must look like 2+ words or be a known name format
            parts = candidate.split()
            if len(parts) >= 2:
                return candidate
    # Fallback: slug → "Jan-de-vries" → "Jan De Vries"
    if slug:
        return ' '.join(w.capitalize() for w in slug.replace('-', ' ').split())
    return 'Unknown Candidate'


# ── GOOGLE SEARCH URL PROCESSING ──────────────────────────────────────────────

_GOOGLE_RESULT_BLOCK_RE = _lre.compile(
    r'<(?:div|li)[^>]*class="[^"]*(?:g|result|gs-result)[^"]*"[^>]*>(.*?)</(?:div|li)>',
    _lre.IGNORECASE | _lre.DOTALL
)
_G_TITLE_RE = _lre.compile(r'<h3[^>]*>(.*?)</h3>', _lre.IGNORECASE | _lre.DOTALL)
_G_SNIPPET_RE = _lre.compile(
    r'(?:<span[^>]*class="[^"]*st[^"]*"[^>]*>|<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>)'
    r'(.*?)</(?:span|div)>',
    _lre.IGNORECASE | _lre.DOTALL
)


def process_google_search_url(source_id: int) -> dict:
    """
    Fetch a Google search URL source, extract LinkedIn profile URLs and result blocks,
    create research queue items. Returns status dict.
    """
    source = get_candidate_source(source_id)
    if not source:
        return {'ok': False, 'error': 'Source not found'}

    url = (source.get('source_url') or '').strip()
    if not url:
        return {'ok': False, 'error': 'No source URL provided'}

    # Update: fetching
    _update_source_fetch_status(source_id, 'Fetching...')

    fetch = fetch_public_url(url)

    if fetch.get('blocked'):
        _update_source_fetch_status(source_id, 'Blocked',
                                    error=fetch.get('error', 'Blocked'),
                                    title=fetch.get('title', ''))
        return {
            'ok': False,
            'blocked': True,
            'error': fetch['error'],
            'manual_review_needed': True,
            'instructions': (
                "Google blocked this automated fetch. "
                "To add these results: open the Google search URL in your browser, "
                "select all visible result text (Ctrl+A or Cmd+A), copy it, "
                "then create a new source using Manual Paste mode and paste the text there."
            ),
        }

    if not fetch['ok']:
        _update_source_fetch_status(source_id, 'Failed', error=fetch.get('error', ''))
        return {'ok': False, 'error': fetch['error']}

    html = fetch['html']
    text = fetch['text_excerpt']
    title = fetch.get('title', '')

    # Extract LinkedIn URLs from both HTML and text
    li_urls = extract_linkedin_profile_urls(html + '\n' + text)

    # Also try to pull structured Google result blocks
    result_blocks = []
    for block_m in _GOOGLE_RESULT_BLOCK_RE.finditer(html):
        block_html = block_m.group(1)
        title_m = _G_TITLE_RE.search(block_html)
        block_title = _html_mod.unescape(_lre.sub(r'<[^>]+>', '', title_m.group(1))) if title_m else ''
        snip_m = _G_SNIPPET_RE.search(block_html)
        block_snip = _html_mod.unescape(_lre.sub(r'<[^>]+>', '', snip_m.group(1))).strip() if snip_m else ''
        block_li_urls = extract_linkedin_profile_urls(block_html)
        if block_title or block_li_urls:
            result_blocks.append({
                'title': block_title,
                'snippet': block_snip,
                'li_urls': block_li_urls,
            })

    excerpt = text[:1500]
    _update_source_fetch_status(source_id, 'Fetched', title=title, excerpt=excerpt)

    # If we got very little useful content, mark as Needs Manual Review
    if not li_urls and len(text) < 200:
        _update_source_fetch_status(source_id, 'Needs Manual Review',
                                    error='Could not extract useful content from Google results page. Please paste results manually.',
                                    title=title, excerpt=excerpt)
        return {
            'ok': False,
            'blocked': False,
            'manual_review_needed': True,
            'error': 'Could not extract useful content.',
            'instructions': (
                "The fetched page had no extractable LinkedIn URLs or candidate text. "
                "Open the Google search URL in your browser, copy all visible result text, "
                "and paste it into a new Manual Paste source."
            ),
        }

    # Build raw_text from extracted blocks + URLs for the existing extractor
    raw_parts = []
    if result_blocks:
        for b in result_blocks:
            parts = []
            if b['title']:
                parts.append(b['title'])
            if b['snippet']:
                parts.append(b['snippet'])
            if b['li_urls']:
                parts.extend(b['li_urls'])
            raw_parts.append('\n'.join(parts))
    elif li_urls:
        raw_parts = li_urls

    # Supplement with plain text from the page
    raw_parts.append(text[:2000])

    combined_raw = '\n\n'.join(raw_parts)

    # Store the combined raw text and re-process
    conn = get_db()
    conn.execute("UPDATE candidate_sources SET raw_text=? WHERE id=?", (combined_raw, source_id))
    conn.commit()
    conn.close()

    created = extract_candidates_from_source(source_id)

    return {
        'ok': True,
        'li_urls_found': len(li_urls),
        'result_blocks_found': len(result_blocks),
        'queue_items_created': len(created),
        'fetch_blocked': False,
    }


def _update_source_fetch_status(source_id: int, status: str,
                                 error: str = '', title: str = '', excerpt: str = ''):
    conn = get_db()
    conn.execute(
        """UPDATE candidate_sources
           SET fetch_status=?, fetch_error=?, fetched_title=?,
               fetched_html_excerpt=?, fetched_at=datetime('now'), updated_at=datetime('now')
           WHERE id=?""",
        (status, error, title, excerpt, source_id)
    )
    conn.commit()
    conn.close()


# ── DIRECT / BATCH URL SOURCE CREATION ────────────────────────────────────────

def create_source_from_url(url: str, source_mode: str,
                            mission_id: int = None,
                            title: str = '') -> int:
    """
    Create a candidate_source for a single URL (Direct Profile URL mode).
    Attempts to extract the slug as a name and creates a queue item.
    Returns source_id.
    """
    url = url.strip()
    # Try to get slug from LinkedIn URL
    slug_m = _LI_SLUG_RE.search(url)
    slug = slug_m.group(1) if slug_m else ''
    name_guess = ' '.join(w.capitalize() for w in slug.replace('-', ' ').split()) if slug else 'Unknown Candidate'

    source_title = title or name_guess or url[:80]

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO candidate_sources
           (source_type, source_name, search_mission_id, raw_text, source_url,
            processed, title, source_mode, fetch_status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        ('direct_profile_url', source_title, mission_id,
         url, url, 0, source_title, source_mode, 'Not Fetched')
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


# ── ENRICHMENT ────────────────────────────────────────────────────────────────

def _compute_confidence(item: dict) -> str:
    """High / Medium / Low confidence based on available data."""
    has_name = item.get('name', '') not in ('', 'Unknown Candidate')
    has_url = bool(item.get('possible_profile_url', ''))
    kw = (item.get('detected_keywords', '') or '') + (item.get('fetched_profile_text', '') or '')
    has_sales_kw = any(k in kw.lower() for k in ['cold call', 'appointment set', 'sdr', 'outbound', 'b2b'])

    if has_name and has_url and has_sales_kw:
        return 'High'
    elif has_url and has_sales_kw:
        return 'Medium'
    else:
        return 'Low'


def enrich_research_candidate(rid: int) -> dict:
    """
    Attempt public enrichment of a research queue item.
    Fetches the public profile URL (if not LinkedIn) or marks as Needs Manual Review.
    Updates the queue item and returns status dict.
    """
    item = get_research_queue_item(rid)
    if not item:
        return {'ok': False, 'error': 'Item not found'}

    url = (item.get('possible_profile_url') or '').strip()
    if not url:
        update_research_queue_item_ext(rid, {
            'enrichment_status': 'Failed',
            'enrichment_error': 'No profile URL available for enrichment',
            'researched_at': now(),
        })
        return {'ok': False, 'error': 'No profile URL'}

    # LinkedIn: always blocked without login
    if 'linkedin.com/in/' in url.lower():
        update_research_queue_item_ext(rid, {
            'enrichment_status': 'Blocked',
            'enrichment_error': (
                'LinkedIn requires login to view profiles. '
                'Open this profile manually in your browser and add visible text via Manual Paste.'
            ),
            'researched_at': now(),
            'confidence_score': _compute_confidence(item),
        })
        mark_needs_manual_review(rid, (
            'LinkedIn profile requires manual review. '
            'Open the profile URL in your browser, copy the visible text, '
            'and add it as a Manual Paste source to enrich this candidate.'
        ))
        return {
            'ok': False,
            'blocked': True,
            'error': 'LinkedIn requires login',
            'manual_review_needed': True,
        }

    # Try fetching non-LinkedIn public page
    fetch = fetch_public_url(url)

    if fetch.get('blocked') or not fetch.get('ok'):
        update_research_queue_item_ext(rid, {
            'enrichment_status': 'Blocked' if fetch.get('blocked') else 'Failed',
            'enrichment_error': fetch.get('error', 'Fetch failed'),
            'researched_at': now(),
            'confidence_score': _compute_confidence(item),
        })
        if fetch.get('blocked'):
            mark_needs_manual_review(rid, fetch.get('error', 'Page blocked'))
        return {'ok': False, 'blocked': fetch.get('blocked', False), 'error': fetch.get('error', '')}

    html = fetch.get('html', '')
    text = fetch.get('text_excerpt', '')
    page_title = fetch.get('title', '')

    # Extract name from page title if we have a better one
    slug_m = _LI_SLUG_RE.search(url)
    slug = slug_m.group(1) if slug_m else ''
    name = _name_from_title(page_title, slug)
    if name and name != 'Unknown Candidate' and item.get('name', '') in ('', 'Unknown Candidate'):
        pass  # will update name below

    # Parse headline / location from text (look for common patterns)
    headline = ''
    location = ''
    about = ''
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Heuristic: first non-empty line after name often contains headline
    for i, line in enumerate(lines[:20]):
        if 'cold call' in line.lower() or 'sales' in line.lower() or 'sdr' in line.lower():
            if not headline:
                headline = line[:200]
        if any(city in line.lower() for city in ['amsterdam', 'rotterdam', 'utrecht', 'netherlands', 'nederland', 'den haag', 'eindhoven']):
            if not location:
                location = line[:100]

    # About: look for a longer descriptive paragraph
    for line in lines:
        if len(line) > 80 and not line.startswith('http'):
            if not about:
                about = line[:500]
                break

    # Re-score with enriched text
    enriched_data = {
        'name': name if name != 'Unknown Candidate' else item.get('name', ''),
        'snippet': item.get('snippet', ''),
        'detected_role': item.get('detected_role', ''),
        'detected_keywords': item.get('detected_keywords', '') + ' ' + text[:500],
    }
    scored = score_research_candidate(enriched_data)
    confidence = _compute_confidence({**item, 'fetched_profile_text': text})

    update_fields = {
        'enrichment_status': 'Fetched',
        'enrichment_error': '',
        'fetched_headline': headline[:300] if headline else '',
        'fetched_location': location[:200] if location else '',
        'fetched_about_excerpt': about[:800] if about else '',
        'fetched_profile_text': text[:2000],
        'researched_at': now(),
        'confidence_score': confidence,
        'score': scored['score'],
        'level': scored['level'],
        'best_role': scored['best_role'],
        'best_offer_type': scored['best_offer_type'],
        'reason': scored['reason'],
        'risk': scored['risk'],
        'next_action': scored['next_action'],
    }
    if name != 'Unknown Candidate' and item.get('name', '') in ('', 'Unknown Candidate'):
        update_fields['name'] = name

    update_research_queue_item_ext(rid, update_fields)
    return {'ok': True, 'confidence': confidence, 'score': scored['score']}


def batch_enrich_research_candidates(source_id: int = None, limit: int = 20) -> dict:
    """Enrich all unenriched queue items, optionally filtered by source."""
    conn = get_db()
    q = """SELECT id FROM candidate_research_queue
           WHERE enrichment_status IN ('Not Started', '')
           AND status NOT IN ('Rejected','Duplicate')"""
    args = []
    if source_id is not None:
        q += " AND candidate_source_id=?"
        args.append(source_id)
    q += f" ORDER BY score DESC LIMIT {limit}"
    ids = [r[0] for r in conn.execute(q, args).fetchall()]
    conn.close()

    results = {'total': len(ids), 'enriched': 0, 'blocked': 0, 'failed': 0}
    for rid in ids:
        r = enrich_research_candidate(rid)
        if r.get('ok'):
            results['enriched'] += 1
        elif r.get('blocked'):
            results['blocked'] += 1
        else:
            results['failed'] += 1
    return results


def mark_needs_manual_review(rid: int, reason: str = ''):
    """Mark a research queue item as Needs Review."""
    update_research_queue_item_ext(rid, {
        'status': 'Needs Review',
        'enrichment_status': 'Needs Manual Review',
        'enrichment_error': reason or 'Manual review required',
        'researched_at': now(),
    })


# ── EXTENDED CRUD (to support new columns) ────────────────────────────────────

def update_candidate_source_ext(sid: int, data: dict):
    """Update candidate_sources using extended field list."""
    conn = get_db()
    sets = []
    vals = []
    for f in _CS_FIELDS_EXT:
        if f in data:
            sets.append(f"{f}=?")
            vals.append(data[f])
    if not sets:
        conn.close(); return
    sets.append("updated_at=datetime('now')")
    vals.append(sid)
    conn.execute(f"UPDATE candidate_sources SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def update_research_queue_item_ext(rid: int, data: dict):
    """Update candidate_research_queue using extended field list."""
    conn = get_db()
    sets = []
    vals = []
    for f in _RQ_FIELDS_EXT:
        if f in data:
            sets.append(f"{f}=?")
            vals.append(data[f])
    if not sets:
        conn.close(); return
    sets.append("updated_at=datetime('now')")
    vals.append(rid)
    conn.execute(f"UPDATE candidate_research_queue SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def get_research_queue_ext(status=None, mission_id=None, source_id=None,
                            enrichment_status=None, confidence=None) -> list:
    """Extended queue query supporting new filter dimensions."""
    conn = get_db()
    q = """SELECT rq.*, sm.name as mission_name
           FROM candidate_research_queue rq
           LEFT JOIN search_missions sm ON rq.search_mission_id=sm.id
           WHERE 1=1"""
    args = []
    if status:
        if isinstance(status, list):
            placeholders = ','.join('?' * len(status))
            q += f" AND rq.status IN ({placeholders})"
            args.extend(status)
        else:
            q += " AND rq.status=?"
            args.append(status)
    if mission_id is not None:
        q += " AND rq.search_mission_id=?"
        args.append(mission_id)
    if source_id is not None:
        q += " AND rq.candidate_source_id=?"
        args.append(source_id)
    if enrichment_status:
        q += " AND rq.enrichment_status=?"
        args.append(enrichment_status)
    if confidence:
        q += " AND rq.confidence_score=?"
        args.append(confidence)
    q += " ORDER BY rq.score DESC, rq.created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_research_summary_ext() -> dict:
    """Extended summary including link-research counts."""
    conn = get_db()
    def _c(q, *a):
        return conn.execute(q, a).fetchone()[0]

    d = {
        'total_sources':         _c("SELECT COUNT(*) FROM candidate_sources"),
        'unprocessed':           _c("SELECT COUNT(*) FROM candidate_sources WHERE processed=0"),
        'sources_needs_fetch':   _c("SELECT COUNT(*) FROM candidate_sources WHERE fetch_status IN ('Not Fetched','')"),
        'sources_blocked':       _c("SELECT COUNT(*) FROM candidate_sources WHERE fetch_status IN ('Blocked','Needs Manual Review')"),
        'queue_total':           _c("SELECT COUNT(*) FROM candidate_research_queue"),
        'queue_new':             _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='New'"),
        'queue_needs_review':    _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Needs Review'"),
        'queue_approved':        _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Approved'"),
        'queue_rejected':        _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Rejected'"),
        'queue_duplicate':       _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Duplicate'"),
        'moved_to_candidates':   _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Moved To Candidates'"),
        'active_missions':       _c("SELECT COUNT(*) FROM search_missions WHERE status='active'"),
        'needs_enrichment':      _c("SELECT COUNT(*) FROM candidate_research_queue WHERE enrichment_status IN ('Not Started','') AND status NOT IN ('Rejected','Duplicate')"),
        'enriched':              _c("SELECT COUNT(*) FROM candidate_research_queue WHERE enrichment_status='Fetched'"),
        'enrichment_blocked':    _c("SELECT COUNT(*) FROM candidate_research_queue WHERE enrichment_status IN ('Blocked','Needs Manual Review')"),
        'high_confidence':       _c("SELECT COUNT(*) FROM candidate_research_queue WHERE confidence_score='High'"),
        'medium_confidence':     _c("SELECT COUNT(*) FROM candidate_research_queue WHERE confidence_score='Medium'"),
    }

    top = conn.execute(
        "SELECT * FROM candidate_research_queue WHERE status NOT IN ('Rejected','Duplicate') ORDER BY score DESC LIMIT 1"
    ).fetchone()
    d['top_candidate'] = to_dict(top)

    conn.close()
    return d



# ══════════════════════════════════════════════════════════════════════════════
# VOICE NOTE SCREENER
# ══════════════════════════════════════════════════════════════════════════════

import json as _json
import tempfile as _tempfile
import urllib.request as _urllib_req

_OPENAI_API_KEY  = os.environ.get('OPENAI_API_KEY', '')
_ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

_AUDIO_CONTENT_TYPES = {
    'audio/ogg', 'audio/mpeg', 'audio/mp4', 'audio/webm',
    'audio/wav', 'audio/x-wav', 'audio/aac', 'audio/flac',
    'audio/m4a', 'audio/x-m4a', 'video/ogg',
}
_AUDIO_EXTENSIONS = ('.ogg', '.mp3', '.mp4', '.m4a', '.wav', '.webm', '.aac', '.flac', '.opus')

_VN_SCORE_WEIGHTS = {
    'score_clarity':            1.0,
    'score_energy':             1.5,
    'score_dutch_level':        2.0,
    'score_structure':          1.0,
    'score_confidence':         1.5,
    'score_objection_handling': 1.5,
    'score_sales_instinct':     2.0,
    'score_coachability':       1.0,
}
_VN_TOTAL_WEIGHT = sum(_VN_SCORE_WEIGHTS.values())

_VN_FIELDS = [
    'candidate_id', 'research_queue_id', 'candidate_name',
    'voice_note_url', 'audio_fetch_status', 'audio_fetch_error',
    'transcript', 'transcript_source', 'transcript_error',
    'score_clarity', 'score_energy', 'score_dutch_level', 'score_structure',
    'score_confidence', 'score_objection_handling', 'score_sales_instinct',
    'score_coachability', 'total_voice_score', 'voice_decision',
    'ai_verdict', 'ai_strengths', 'ai_risks', 'ai_recommendation',
    'status', 'notes', 'reviewed_by', 'scored_at', 'reviewed_at',
]


def init_voice_note_tables():
    """Create voice_note_screens table. Safe to call multiple times."""
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS voice_note_screens (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id            INTEGER REFERENCES cold_caller_candidates(id) ON DELETE SET NULL,
        research_queue_id       INTEGER,
        candidate_name          TEXT NOT NULL,
        voice_note_url          TEXT,
        audio_fetch_status      TEXT DEFAULT 'Not Fetched',
        audio_fetch_error       TEXT,
        transcript              TEXT,
        transcript_source       TEXT DEFAULT 'Pending',
        transcript_error        TEXT,
        score_clarity           INTEGER DEFAULT 0,
        score_energy            INTEGER DEFAULT 0,
        score_dutch_level       INTEGER DEFAULT 0,
        score_structure         INTEGER DEFAULT 0,
        score_confidence        INTEGER DEFAULT 0,
        score_objection_handling INTEGER DEFAULT 0,
        score_sales_instinct    INTEGER DEFAULT 0,
        score_coachability      INTEGER DEFAULT 0,
        total_voice_score       INTEGER DEFAULT 0,
        voice_decision          TEXT DEFAULT 'Pending',
        ai_verdict              TEXT,
        ai_strengths            TEXT,
        ai_risks                TEXT,
        ai_recommendation       TEXT,
        status                  TEXT DEFAULT 'Pending',
        notes                   TEXT,
        reviewed_by             TEXT,
        created_at              TEXT DEFAULT (datetime('now')),
        scored_at               TEXT,
        reviewed_at             TEXT
    )
    """)
    conn.commit()
    conn.close()


def _compute_voice_score(row: dict) -> tuple:
    """Return (total_score 0-100, voice_decision str)."""
    raw = 0.0
    for field, weight in _VN_SCORE_WEIGHTS.items():
        raw += int(row.get(field) or 0) * weight
    normalized = int(round((raw / (10.0 * _VN_TOTAL_WEIGHT)) * 100))
    normalized = max(0, min(100, normalized))
    if normalized >= 80:
        decision = 'A-Candidate'
    elif normalized >= 65:
        decision = 'B-Candidate'
    elif normalized >= 50:
        decision = 'Nurture'
    else:
        decision = 'Reject'
    return normalized, decision


def _fetch_audio_bytes(url: str) -> dict:
    """
    Attempt to download audio from a URL.
    Returns {ok, bytes, content_type, error, extension}.
    Only accepts audio/* content types or audio file extensions.
    """
    result = {'ok': False, 'bytes': None, 'content_type': '', 'error': '', 'extension': '.ogg'}
    try:
        req = _urllib_req.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; MapleOS/1.0)',
        })
        with _urllib_req.urlopen(req, timeout=30) as resp:
            ct = resp.headers.get('Content-Type', '').split(';')[0].strip().lower()
            # Check content type or file extension
            ext_ok = any(url.lower().endswith(e) for e in _AUDIO_EXTENSIONS)
            ct_ok  = any(ct.startswith(a) for a in _AUDIO_CONTENT_TYPES)
            if not (ct_ok or ext_ok):
                result['error'] = f'Not an audio file (Content-Type: {ct or "unknown"}). Paste the transcript manually.'
                return result
            data = resp.read(20 * 1024 * 1024)  # 20 MB limit
            if not data:
                result['error'] = 'Empty audio response'
                return result
            # Determine extension
            for ext in _AUDIO_EXTENSIONS:
                if url.lower().endswith(ext) or ct.endswith(ext.lstrip('.')):
                    result['extension'] = ext
                    break
            if ct == 'audio/ogg' or 'ogg' in ct:
                result['extension'] = '.ogg'
            elif ct == 'audio/mpeg' or 'mp3' in ct:
                result['extension'] = '.mp3'
            elif ct in ('audio/mp4', 'audio/x-m4a', 'audio/m4a'):
                result['extension'] = '.m4a'
            elif ct == 'audio/webm':
                result['extension'] = '.webm'
            result.update({'ok': True, 'bytes': data, 'content_type': ct})
    except Exception as e:
        result['error'] = f'Could not download audio: {e}'
    return result


def transcribe_voice_note(vn_id: int) -> dict:
    """
    Download audio from URL and transcribe via OpenAI Whisper.
    Returns {ok, transcript, source, error}.
    Updates the voice_note_screens row.
    """
    if not _OPENAI_API_KEY:
        _update_vn({'audio_fetch_status': 'No API Key',
                    'transcript_source': 'Manual',
                    'transcript_error': 'OpenAI API key not configured. Paste transcript manually.'}, vn_id)
        return {'ok': False, 'error': 'OpenAI API key not configured', 'needs_manual': True}

    conn = get_db()
    row = to_dict(conn.execute("SELECT * FROM voice_note_screens WHERE id=?", (vn_id,)).fetchone())
    conn.close()
    if not row:
        return {'ok': False, 'error': 'Screen not found'}

    url = (row.get('voice_note_url') or '').strip()
    if not url:
        return {'ok': False, 'error': 'No URL provided', 'needs_manual': True}

    _update_vn({'audio_fetch_status': 'Fetching'}, vn_id)

    audio = _fetch_audio_bytes(url)
    if not audio['ok']:
        _update_vn({'audio_fetch_status': 'Failed',
                    'audio_fetch_error': audio['error'],
                    'transcript_source': 'Manual',
                    'transcript_error': audio['error']}, vn_id)
        return {'ok': False, 'error': audio['error'], 'needs_manual': True}

    _update_vn({'audio_fetch_status': 'Fetched'}, vn_id)

    # Write to temp file and call Whisper
    try:
        import openai as _openai
    except ImportError:
        _update_vn({'transcript_source': 'Manual',
                    'transcript_error': 'openai package not installed'}, vn_id)
        return {'ok': False, 'error': 'openai package not installed. Run: pip install openai', 'needs_manual': True}

    try:
        client = _openai.OpenAI(api_key=_OPENAI_API_KEY)
        with _tempfile.NamedTemporaryFile(suffix=audio['extension'], delete=False) as f:
            f.write(audio['bytes'])
            tmp_path = f.name
        with open(tmp_path, 'rb') as f:
            resp = client.audio.transcriptions.create(
                model='whisper-1',
                file=f,
                language='nl',
            )
        transcript = resp.text
        _update_vn({'transcript': transcript, 'transcript_source': 'Whisper',
                    'transcript_error': None, 'status': 'Transcribed'}, vn_id)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return {'ok': True, 'transcript': transcript, 'source': 'Whisper'}
    except Exception as e:
        err = str(e)
        _update_vn({'audio_fetch_status': 'Fetched',
                    'transcript_source': 'Failed',
                    'transcript_error': err}, vn_id)
        return {'ok': False, 'error': err, 'needs_manual': True}


def score_voice_note_with_ai(vn_id: int) -> dict:
    """
    Score an existing transcript using Claude.
    Returns {ok, scores, error}.
    Updates the voice_note_screens row with all scores + AI verdict.
    """
    if not _ANTHROPIC_API_KEY:
        return {'ok': False, 'error': 'Anthropic API key not configured. Score manually.', 'needs_manual': True}

    conn = get_db()
    row = to_dict(conn.execute("SELECT * FROM voice_note_screens WHERE id=?", (vn_id,)).fetchone())
    conn.close()
    if not row:
        return {'ok': False, 'error': 'Screen not found'}

    transcript = (row.get('transcript') or '').strip()
    if len(transcript) < 20:
        return {'ok': False, 'error': 'Transcript too short to score. Please verify the transcript.'}

    prompt = f"""You are scoring a Dutch cold-calling candidate based on their voice note transcript.
The candidate is applying for a cold calling / appointment setting / sales role in the Netherlands.
The company (Maple) recruits Dutch-speaking remote sales talent.

Rate each dimension from 1 (very poor) to 10 (excellent).
Be critical and realistic. Do not give 7-8 unless genuinely earned.

TRANSCRIPT:
{transcript[:3000]}

Return ONLY valid JSON — no explanation outside the JSON block:
{{
  "score_clarity": <1-10>,
  "score_energy": <1-10>,
  "score_dutch_level": <1-10>,
  "score_structure": <1-10>,
  "score_confidence": <1-10>,
  "score_objection_handling": <1-10>,
  "score_sales_instinct": <1-10>,
  "score_coachability": <1-10>,
  "ai_strengths": "<2-3 key strengths observed in the voice note>",
  "ai_risks": "<2-3 red flags or concerns>",
  "ai_verdict": "<one sentence overall judgment: would you move this person forward?>",
  "ai_recommendation": "<exact next action: Plan Test Call / Send to B-pipeline / Nurture / Reject>"
}}

Scoring guide:
- score_clarity: How clear and articulate is their speech? Can you understand every word?
- score_energy: Do they sound energetic, motivated, alive? Cold calling needs energy.
- score_dutch_level: Is their Dutch native/near-native? Grade strictly: accent, grammar, fluency.
- score_structure: Do they have a logical intro, body, close? Are they rambling?
- score_confidence: Do they sound confident and assertive (not arrogant)?
- score_objection_handling: Did they handle the "why should we hire you" angle well?
- score_sales_instinct: Do they show commercial thinking, positioning, value communication?
- score_coachability: Do they show self-awareness, openness to feedback, growth mindset?"""

    try:
        import anthropic as _anthropic
    except ImportError:
        return {'ok': False, 'error': 'anthropic package not installed. Run: pip install anthropic', 'needs_manual': True}

    try:
        client = _anthropic.Anthropic(api_key=_ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw
            raw = raw.rsplit('```', 1)[0].strip()
        scores = _json.loads(raw)
    except _json.JSONDecodeError as e:
        return {'ok': False, 'error': f'AI returned invalid JSON: {e}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    # Compute weighted total
    total, decision = _compute_voice_score(scores)

    update_data = {
        'score_clarity':             int(scores.get('score_clarity', 0)),
        'score_energy':              int(scores.get('score_energy', 0)),
        'score_dutch_level':         int(scores.get('score_dutch_level', 0)),
        'score_structure':           int(scores.get('score_structure', 0)),
        'score_confidence':          int(scores.get('score_confidence', 0)),
        'score_objection_handling':  int(scores.get('score_objection_handling', 0)),
        'score_sales_instinct':      int(scores.get('score_sales_instinct', 0)),
        'score_coachability':        int(scores.get('score_coachability', 0)),
        'total_voice_score':         total,
        'voice_decision':            decision,
        'ai_strengths':              scores.get('ai_strengths', ''),
        'ai_risks':                  scores.get('ai_risks', ''),
        'ai_verdict':                scores.get('ai_verdict', ''),
        'ai_recommendation':         scores.get('ai_recommendation', ''),
        'status':                    'Scored',
        'scored_at':                 now(),
    }
    _update_vn(update_data, vn_id)
    return {'ok': True, 'scores': update_data, 'total': total, 'decision': decision}


def save_manual_transcript(vn_id: int, transcript: str) -> dict:
    """Save a manually pasted transcript and mark status."""
    transcript = (transcript or '').strip()
    if not transcript:
        return {'ok': False, 'error': 'Transcript is empty'}
    _update_vn({
        'transcript': transcript,
        'transcript_source': 'Manual',
        'transcript_error': None,
        'audio_fetch_status': 'Manual',
        'status': 'Transcribed',
    }, vn_id)
    return {'ok': True}


def save_manual_scores(vn_id: int, data: dict) -> dict:
    """Save manually entered scores, compute total + decision."""
    score_fields = [
        'score_clarity', 'score_energy', 'score_dutch_level', 'score_structure',
        'score_confidence', 'score_objection_handling', 'score_sales_instinct',
        'score_coachability',
    ]
    scores = {}
    for f in score_fields:
        try:
            scores[f] = max(0, min(10, int(data.get(f, 0) or 0)))
        except (ValueError, TypeError):
            scores[f] = 0

    total, decision = _compute_voice_score(scores)
    update = dict(scores)
    update.update({
        'total_voice_score': total,
        'voice_decision':    decision,
        'ai_verdict':        (data.get('ai_verdict') or '').strip() or None,
        'ai_strengths':      (data.get('ai_strengths') or '').strip() or None,
        'ai_risks':          (data.get('ai_risks') or '').strip() or None,
        'ai_recommendation': (data.get('ai_recommendation') or '').strip() or None,
        'status':            'Scored',
        'scored_at':         now(),
    })
    _update_vn(update, vn_id)
    return {'ok': True, 'total': total, 'decision': decision}


def _update_vn(data: dict, vn_id: int):
    """Internal helper — write any subset of fields to voice_note_screens."""
    if not data:
        return
    sets = ', '.join(f'{k}=?' for k in data)
    vals = list(data.values()) + [vn_id]
    conn = get_db()
    conn.execute(f"UPDATE voice_note_screens SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def create_voice_note_screen(data: dict) -> int:
    """Create a new voice note screen record. Returns new id."""
    conn = get_db()
    fields = [f for f in _VN_FIELDS if f in data]
    vals   = [data[f] for f in fields]
    ph     = ','.join(['?'] * len(fields))
    cols   = ','.join(fields)
    c = conn.execute(f"INSERT INTO voice_note_screens ({cols}) VALUES ({ph})", vals)
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def get_voice_note_screen(vn_id: int) -> dict:
    conn = get_db()
    row  = to_dict(conn.execute(
        "SELECT vn.*, c.full_name AS linked_candidate_name "
        "FROM voice_note_screens vn "
        "LEFT JOIN cold_caller_candidates c ON c.id = vn.candidate_id "
        "WHERE vn.id=?", (vn_id,)).fetchone())
    conn.close()
    return row


def get_voice_note_screens(candidate_id=None, status='', decision='') -> list:
    conn = get_db()
    q    = ("SELECT vn.*, c.full_name AS linked_candidate_name "
            "FROM voice_note_screens vn "
            "LEFT JOIN cold_caller_candidates c ON c.id = vn.candidate_id WHERE 1=1")
    args = []
    if candidate_id:
        q += " AND vn.candidate_id=?"; args.append(candidate_id)
    if status:
        q += " AND vn.status=?"; args.append(status)
    if decision:
        q += " AND vn.voice_decision=?"; args.append(decision)
    q += " ORDER BY vn.created_at DESC"
    rows = to_list(conn.execute(q, args).fetchall())
    conn.close()
    return rows


def get_voice_note_summary() -> dict:
    conn = get_db()
    def _c(sql): return conn.execute(sql).fetchone()[0]
    try:
        d = {
            'total':       _c("SELECT COUNT(*) FROM voice_note_screens"),
            'pending':     _c("SELECT COUNT(*) FROM voice_note_screens WHERE status='Pending'"),
            'transcribed': _c("SELECT COUNT(*) FROM voice_note_screens WHERE status='Transcribed'"),
            'scored':      _c("SELECT COUNT(*) FROM voice_note_screens WHERE status='Scored'"),
            'approved':    _c("SELECT COUNT(*) FROM voice_note_screens WHERE status='Approved'"),
            'rejected':    _c("SELECT COUNT(*) FROM voice_note_screens WHERE status='Rejected'"),
            'a_candidates':_c("SELECT COUNT(*) FROM voice_note_screens WHERE voice_decision='A-Candidate'"),
            'b_candidates':_c("SELECT COUNT(*) FROM voice_note_screens WHERE voice_decision='B-Candidate'"),
        }
    except Exception:
        d = {k: 0 for k in ('total','pending','transcribed','scored','approved','rejected','a_candidates','b_candidates')}
    conn.close()
    return d


def approve_voice_note(vn_id: int) -> dict:
    """Approve a voice note screen. Creates 'Plan Test Call' action task."""
    row = get_voice_note_screen(vn_id)
    if not row:
        return {'ok': False, 'error': 'Not found'}
    _update_vn({'status': 'Approved', 'reviewed_at': now()}, vn_id)

    # Create action task
    task_id = None
    try:
        name  = row.get('candidate_name') or 'Candidate'
        score = row.get('total_voice_score') or 0
        dec   = row.get('voice_decision') or ''
        verdict = row.get('ai_verdict') or ''
        task_data = {
            'task_type':    'Plan Test Call',
            'title':        f'Plan Test Call — {name}',
            'description':  f'Voice note approved. Score: {score}/100 ({dec}). {verdict}'.strip(),
            'priority':     'High' if dec == 'A-Candidate' else 'Medium',
            'status':       'Pending',
            'owner':        'Rutger',
            'related_type': 'voice_note_screen',
            'related_id':   vn_id,
        }
        if row.get('candidate_id'):
            task_data['candidate_id'] = row['candidate_id']
        task_id = create_action_task(task_data)
    except Exception:
        pass

    return {'ok': True, 'task_id': task_id}


def reject_voice_note(vn_id: int, reason: str = '') -> dict:
    """Reject a voice note screen. Creates 'Reject Candidate' action task."""
    row = get_voice_note_screen(vn_id)
    if not row:
        return {'ok': False, 'error': 'Not found'}
    _update_vn({'status': 'Rejected', 'reviewed_at': now()}, vn_id)

    task_id = None
    try:
        name = row.get('candidate_name') or 'Candidate'
        task_data = {
            'task_type':    'Reject Candidate',
            'title':        f'Reject Candidate — {name}',
            'description':  reason or f'Voice note rejected. Score: {row.get("total_voice_score", 0)}/100 ({row.get("voice_decision", "")}).',
            'priority':     'Low',
            'status':       'Pending',
            'owner':        'Rutger',
            'related_type': 'voice_note_screen',
            'related_id':   vn_id,
        }
        if row.get('candidate_id'):
            task_data['candidate_id'] = row['candidate_id']
        task_id = create_action_task(task_data)
    except Exception:
        pass

    return {'ok': True, 'task_id': task_id}


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER / DASHBOARD DATA
# ══════════════════════════════════════════════════════════════════════════════

def get_dashboard_data() -> dict:
    """
    Aggregates all data needed by the Command Center dashboard.
    Returns a single dict. Safe even if tables don't exist yet.
    """
    conn = get_db()
    def _c(sql, default=0):
        try: return conn.execute(sql).fetchone()[0]
        except Exception: return default

    d = {}

    # ── Candidate pipeline ────────────────────────────────────────────────────
    d['candidates_total']     = _c("SELECT COUNT(*) FROM cold_caller_candidates")
    d['candidates_new']       = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='found'")
    d['candidates_contacted'] = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='contacted'")
    d['candidates_replied']   = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='replied'")
    d['candidates_qualified'] = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='qualified'")
    d['candidates_interview'] = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='interview'")
    d['candidates_placed']    = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='placed'")
    d['candidates_rejected']  = _c("SELECT COUNT(*) FROM cold_caller_candidates WHERE status='rejected'")

    # ── Research pipeline ─────────────────────────────────────────────────────
    d['sources_total']           = _c("SELECT COUNT(*) FROM candidate_sources")
    d['sources_unprocessed']     = _c("SELECT COUNT(*) FROM candidate_sources WHERE processed=0")
    d['sources_needs_fetch']     = _c("SELECT COUNT(*) FROM candidate_sources WHERE fetch_status IN ('Not Fetched','')")
    d['sources_blocked']         = _c("SELECT COUNT(*) FROM candidate_sources WHERE fetch_status IN ('Blocked','Needs Manual Review')")
    d['queue_total']             = _c("SELECT COUNT(*) FROM candidate_research_queue")
    d['queue_new']               = _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='New'")
    d['queue_needs_review']      = _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Needs Review'")
    d['queue_approved']          = _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Approved'")
    d['queue_moved']             = _c("SELECT COUNT(*) FROM candidate_research_queue WHERE status='Moved To Candidates'")
    d['queue_blocked']           = _c("SELECT COUNT(*) FROM candidate_research_queue WHERE enrichment_status IN ('Blocked','Needs Manual Review')")
    # keep legacy keys for any existing code
    d['research_sources_unprocessed'] = d['sources_unprocessed']
    d['research_queue_new']           = d['queue_new']
    d['research_queue_needs_review']  = d['queue_needs_review']
    d['research_queue_approved']      = d['queue_approved']

    # ── Source queue (candidate_source_queue) ─────────────────────────────────
    d['sq_total']     = _c("SELECT COUNT(*) FROM candidate_source_queue")
    d['sq_queued']    = _c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='queued'")
    d['sq_tier_a']    = _c("SELECT COUNT(*) FROM candidate_source_queue WHERE tier='A' AND status='queued'")
    d['sq_tier_b']    = _c("SELECT COUNT(*) FROM candidate_source_queue WHERE tier='B' AND status='queued'")
    d['sq_approved']  = _c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='approved'")
    d['sq_converted'] = _c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='converted'")
    d['sq_rejected']  = _c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='rejected'")

    # ── Action tasks ──────────────────────────────────────────────────────────
    _ACTIVE = "status NOT IN ('Completed','Rejected')"
    _PRIO   = "CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"
    try:
        d['tasks_pending']        = _c("SELECT COUNT(*) FROM action_tasks WHERE status='Pending'")
        d['tasks_open']           = _c(f"SELECT COUNT(*) FROM action_tasks WHERE {_ACTIVE}")
        d['tasks_overdue']        = _c(
            f"SELECT COUNT(*) FROM action_tasks WHERE {_ACTIVE} "
            "AND due_date IS NOT NULL AND due_date < date('now')")
        d['tasks_due_today']      = _c(
            f"SELECT COUNT(*) FROM action_tasks WHERE {_ACTIVE} "
            "AND due_date = date('now')")
        d['tasks_copied']         = _c("SELECT COUNT(*) FROM action_tasks WHERE status='Copied'")
        d['tasks_sent']           = _c("SELECT COUNT(*) FROM action_tasks WHERE status='Sent'")
        d['tasks_completed_today']= _c(
            "SELECT COUNT(*) FROM action_tasks WHERE status='Completed' "
            "AND completed_at >= date('now')")
        d['tasks_blocked']        = _c(
            "SELECT COUNT(*) FROM action_tasks WHERE status IN ('Blocked','Needs Review')")
        # Top overdue task (Critical/High first)
        overdue_row = conn.execute(
            f"SELECT * FROM action_tasks WHERE {_ACTIVE} "
            "AND due_date IS NOT NULL AND due_date < date('now') "
            f"ORDER BY {_PRIO}, due_date ASC LIMIT 1"
        ).fetchone()
        d['top_overdue_task'] = to_dict(overdue_row)
        # Top due-today task
        today_row = conn.execute(
            f"SELECT * FROM action_tasks WHERE {_ACTIVE} "
            "AND due_date = date('now') "
            f"ORDER BY {_PRIO}, created_at ASC LIMIT 1"
        ).fetchone()
        d['top_today_task'] = to_dict(today_row)
        # Top pending task overall
        top_task = conn.execute(
            f"SELECT * FROM action_tasks WHERE status='Pending' "
            f"ORDER BY {_PRIO}, created_at ASC LIMIT 1"
        ).fetchone()
        d['top_task'] = to_dict(top_task)
        # Tasks copied and ready to send
        d['tasks_ready_to_send'] = to_list(conn.execute(
            "SELECT id, title, task_type, priority FROM action_tasks "
            "WHERE status='Copied' ORDER BY created_at ASC LIMIT 5"
        ).fetchall())
    except Exception:
        d['tasks_pending'] = d['tasks_open'] = d['tasks_overdue'] = 0
        d['tasks_due_today'] = d['tasks_copied'] = d['tasks_sent'] = 0
        d['tasks_completed_today'] = d['tasks_blocked'] = 0
        d['top_overdue_task'] = d['top_today_task'] = d['top_task'] = None
        d['tasks_ready_to_send'] = []

    # ── Voice notes ───────────────────────────────────────────────────────────
    try:
        d['voice_notes_pending'] = _c(
            "SELECT COUNT(*) FROM voice_note_screens WHERE status IN ('Pending','Transcribed')")
        d['voice_notes_scored']  = _c(
            "SELECT COUNT(*) FROM voice_note_screens WHERE status='Scored'")
        d['voice_notes_a']       = _c(
            "SELECT COUNT(*) FROM voice_note_screens WHERE voice_decision='A-Candidate'")
    except Exception:
        d['voice_notes_pending'] = d['voice_notes_scored'] = d['voice_notes_a'] = 0

    # ── Observer ──────────────────────────────────────────────────────────────
    try:
        d['observer_open'] = _c(
            "SELECT COUNT(*) FROM observer_recommendations WHERE status='open'")
        obs_top = conn.execute(
            "SELECT * FROM observer_recommendations WHERE status='open' "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        d['observer_top'] = to_dict(obs_top)
    except Exception:
        d['observer_open'] = 0
        d['observer_top'] = None

    # ── Agents ────────────────────────────────────────────────────────────────
    try:
        d['agents'] = to_list(conn.execute(
            "SELECT id, name, type, enabled, last_run_at, latest_output, "
            "current_issue, recommendation FROM agents ORDER BY type"
        ).fetchall())
    except Exception:
        d['agents'] = []

    # ── "Needs Your Approval" items ───────────────────────────────────────────
    needs_approval = []
    # 1. Research queue: New + Needs Review
    try:
        for r in to_list(conn.execute(
            "SELECT id, name, score, level, status FROM candidate_research_queue "
            "WHERE status IN ('New','Needs Review') ORDER BY score DESC LIMIT 5"
        ).fetchall()):
            needs_approval.append({
                'type': 'Research Candidate',
                'label': r['name'],
                'detail': f"Score {r['score']} ({r['level']}) — {r['status']}",
                'url': f"/research/queue/{r['id']}",
            })
    except Exception:
        pass
    # 2. Action tasks: Copied (ready to send) + Blocked/Needs Review
    try:
        for t in to_list(conn.execute(
            "SELECT id, title, task_type, priority, status FROM action_tasks "
            "WHERE status IN ('Copied','Blocked','Needs Review') "
            "ORDER BY CASE status WHEN 'Copied' THEN 0 WHEN 'Needs Review' THEN 1 ELSE 2 END, "
            "CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 ELSE 2 END LIMIT 5"
        ).fetchall()):
            needs_approval.append({
                'type': t['task_type'] or 'Task',
                'label': t['title'],
                'detail': f"Status: {t['status']} — Priority: {t['priority']}",
                'url': f"/tasks/{t['id']}",
            })
    except Exception:
        pass
    # 3. Voice notes scored but not approved/rejected
    try:
        for v in to_list(conn.execute(
            "SELECT id, candidate_name, total_voice_score, voice_decision "
            "FROM voice_note_screens WHERE status='Scored' "
            "ORDER BY total_voice_score DESC LIMIT 3"
        ).fetchall()):
            needs_approval.append({
                'type': 'Voice Note',
                'label': v['candidate_name'],
                'detail': f"Score {v['total_voice_score']}/100 — {v['voice_decision']}",
                'url': f"/voice-notes/{v['id']}",
            })
    except Exception:
        pass
    # 4. Source queue: approved but not yet converted to candidate
    try:
        for s in to_list(conn.execute(
            "SELECT id, name, tier, score FROM candidate_source_queue "
            "WHERE status='approved' AND candidate_id IS NULL LIMIT 3"
        ).fetchall()):
            needs_approval.append({
                'type': 'Source Approved',
                'label': s['name'],
                'detail': f"Tier {s['tier']} — Score {s['score']} — needs candidate creation",
                'url': f"/sources/{s['id']}",
            })
    except Exception:
        pass
    d['needs_approval'] = needs_approval

    # ── Highest ROI action ─────────────────────────────────────────────────────
    # Priority chain:
    # 1. Overdue Critical/High task
    # 2. Task due today
    # 3. Source queue A/B tier candidates queued
    # 4. Research queue Needs Review
    # 5. Research queue New
    # 6. Unprocessed research sources
    # 7. Open observer recommendations
    # 8. Default: add source / run agent
    roi = None
    _overdue_critical = _c(
        "SELECT COUNT(*) FROM action_tasks "
        "WHERE status NOT IN ('Completed','Rejected') "
        "AND due_date IS NOT NULL AND due_date < date('now') "
        "AND priority IN ('Critical','High')"
    )
    if _overdue_critical > 0 and d.get('top_overdue_task'):
        t = d['top_overdue_task']
        roi = {
            'title': 'Overdue Critical/High Task',
            'reason': f"Task has passed its due date — priority: {t.get('priority','?')}",
            'action_label': 'Open Task →',
            'action_url': f"/tasks/{t['id']}",
            'secondary_label': 'All Tasks',
            'secondary_url': '/tasks',
            'level': 'urgent',
        }
    elif d.get('tasks_overdue', 0) > 0 and d.get('top_overdue_task'):
        t = d['top_overdue_task']
        roi = {
            'title': 'Overdue Task',
            'reason': f"\"{t.get('title','Task')}\" passed its due date",
            'action_label': 'Open Task →',
            'action_url': f"/tasks/{t['id']}",
            'secondary_label': 'All Tasks',
            'secondary_url': '/tasks',
            'level': 'urgent',
        }
    elif d.get('tasks_due_today', 0) > 0 and d.get('top_today_task'):
        t = d['top_today_task']
        roi = {
            'title': 'Task Due Today',
            'reason': f"\"{t.get('title','Task')}\" is due today",
            'action_label': 'Open Task →',
            'action_url': f"/tasks/{t['id']}",
            'secondary_label': 'All Tasks',
            'secondary_url': '/tasks',
            'level': 'high',
        }
    elif d.get('sq_tier_a', 0) + d.get('sq_tier_b', 0) > 0:
        n = d['sq_tier_a'] + d['sq_tier_b']
        roi = {
            'title': 'Source Queue: A/B Candidates Waiting',
            'reason': f"{n} high-scoring profile(s) in the source queue need review",
            'action_label': 'Review Source Queue →',
            'action_url': '/sources',
            'secondary_label': 'Add Profile',
            'secondary_url': '/sources/new',
            'level': 'high',
        }
    elif d.get('queue_needs_review', 0) > 0:
        roi = {
            'title': 'Research Queue: Candidates Need Review',
            'reason': f"{d['queue_needs_review']} candidate(s) flagged for your review",
            'action_label': 'Review Candidates →',
            'action_url': '/research/queue?status=Needs+Review',
            'secondary_label': 'All Queue',
            'secondary_url': '/research/queue',
            'level': 'high',
        }
    elif d.get('queue_new', 0) > 0:
        roi = {
            'title': 'New Candidates in Research Queue',
            'reason': f"{d['queue_new']} new candidate(s) waiting for your decision",
            'action_label': 'Open Review Queue →',
            'action_url': '/research/queue',
            'secondary_label': 'Research Hub',
            'secondary_url': '/research',
            'level': 'medium',
        }
    elif d.get('sources_unprocessed', 0) > 0:
        roi = {
            'title': 'Unprocessed Research Sources',
            'reason': f"{d['sources_unprocessed']} source(s) haven't been processed yet",
            'action_label': 'Process Sources →',
            'action_url': '/research/sources',
            'secondary_label': 'Add Source',
            'secondary_url': '/research/url',
            'level': 'medium',
        }
    elif d.get('observer_open', 0) > 0 and d.get('observer_top'):
        obs = d['observer_top']
        roi = {
            'title': 'Observer Recommendation Open',
            'reason': obs.get('bottleneck') or 'Observer has flagged a bottleneck',
            'action_label': 'View Observer →',
            'action_url': '/observer',
            'secondary_label': None,
            'secondary_url': None,
            'level': 'medium',
        }
    elif d.get('candidates_total', 0) == 0:
        roi = {
            'title': 'Get Started: Add Your First Source',
            'reason': 'No candidates yet — add a LinkedIn URL or paste a profile to begin',
            'action_label': 'Add Research Source →',
            'action_url': '/research/url',
            'secondary_label': 'Paste Profile',
            'secondary_url': '/sources/new',
            'level': 'info',
        }
    else:
        # Find the candidate research worker agent
        crw = None
        for ag in d.get('agents', []):
            if 'research' in (ag.get('type') or '').lower() or 'research' in (ag.get('name') or '').lower():
                crw = ag
                break
        if crw:
            roi = {
                'title': 'Run Candidate Research Worker',
                'reason': 'No urgent actions — run the agent to find new candidates',
                'action_label': 'Run Agent →',
                'action_url': f"/agents/{crw['id']}/run",
                'secondary_label': 'All Agents',
                'secondary_url': '/agents',
                'level': 'info',
            }
        else:
            roi = {
                'title': 'Add a Research Source',
                'reason': 'No urgent actions — add a source URL to find new candidates',
                'action_label': 'Add Source →',
                'action_url': '/research/url',
                'secondary_label': 'Research Hub',
                'secondary_url': '/research',
                'level': 'info',
            }
    d['highest_roi'] = roi

    conn.close()
    return d


# ══════════════════════════════════════════════════════════════════════════════
# CANDIDATE SOURCE QUEUE — input parser + rule-based scorer
# ══════════════════════════════════════════════════════════════════════════════

def init_source_queue_table():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS candidate_source_queue (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        name               TEXT NOT NULL,
        source_type        TEXT DEFAULT 'Manual',
        profile_url        TEXT,
        raw_profile_text   TEXT,
        parsed_json        TEXT,
        score              INTEGER DEFAULT 0,
        tier               TEXT DEFAULT 'Unscored',
        reasons_json       TEXT,
        recommended_action TEXT,
        notes              TEXT,
        status             TEXT DEFAULT 'queued',
        candidate_id       INTEGER,
        created_at         TEXT DEFAULT (datetime('now')),
        updated_at         TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()


def _parse_source_profile(text: str) -> dict:
    """Extract structured signals from raw profile text. Pure rule-based, no AI."""
    import re
    text_lower = (text or '').lower()

    parsed = {
        'role': None,
        'location': None,
        'language_signals': [],
        'sales_signals': [],
        'remote_signals': [],
        'red_flags': [],
        'has_proof': False,
    }

    if not text_lower.strip():
        return parsed

    # Role/title — first non-empty line or explicit label
    for pattern in [
        r'(?:role|title|functie|position|werkzaam als|werkt als)[:\s]+([^\n,]{3,80})',
        r'^([A-Z][^\n]{3,60})$',
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            parsed['role'] = m.group(1).strip()[:100]
            break

    # Location (Dutch cities + country signals)
    dutch_locations = [
        'amsterdam', 'rotterdam', 'den haag', 'the hague', 'utrecht',
        'eindhoven', 'groningen', 'breda', 'tilburg', 'almere',
        'nijmegen', 'apeldoorn', 'haarlem', 'arnhem', 'enschede',
        'leiden', 'zoetermeer', 'maastricht', 'zwolle', 'alkmaar',
        'nederland', 'netherlands', 'holland',
    ]
    for loc in dutch_locations:
        if loc in text_lower:
            parsed['location'] = loc
            break
    # Also detect standalone NL (not as part of URL)
    if not parsed['location'] and re.search(r'\bNL\b', text):
        parsed['location'] = 'nl'

    # Dutch language signals
    dutch_words = [
        'ik ben', 'ik heb', 'mijn ', 'jaar ervaring', 'werkzaam',
        'acquisitie', 'verkoop', 'bellen', 'klanten', 'bedrijven',
        'afsluiten', 'offertes', 'omzet', 'provisie', 'thuiswerk',
    ]
    for w in dutch_words:
        if w in text_lower:
            parsed['language_signals'].append(f'NL: "{w.strip()}"')

    # Sales experience signals
    sales_keywords = {
        'cold call':                    'cold calling',
        'cold calling':                 'cold calling',
        'appointment setting':          'appointment setting',
        'appointment setter':           'appointment setting',
        'acquisitie':                   'cold calling (NL)',
        'telefonische acquisitie':      'cold calling (NL)',
        'telefonische verkoop':         'cold calling (NL)',
        'b2b':                          'B2B sales',
        'business to business':         'B2B sales',
        'closer':                       'sales closer',
        'closing':                      'sales closer',
        'high ticket':                  'high-ticket sales',
        'high-ticket':                  'high-ticket sales',
        'recruitment':                  'recruitment/staffing',
        'recruiter':                    'recruitment/staffing',
        'headhunter':                   'recruitment/staffing',
        'account manager':              'account management',
        'account management':           'account management',
        'business development':         'business development',
        'lead generation':              'lead generation',
        'lead gen':                     'lead generation',
        'outbound':                     'outbound sales',
        'inside sales':                 'inside sales',
        'field sales':                  'field sales',
        'outdoor sales':                'outdoor/field sales',
        'd2d':                          'door-to-door',
        'door to door':                 'door-to-door',
        'deur aan deur':                'door-to-door (NL)',
        'sales':                        'general sales',
        'verkoop':                      'sales (NL)',
        'vertegenwoordiger':            'sales rep (NL)',
        'commercieel':                  'commercial (NL)',
        'telesales':                    'telesales',
        'televerkoop':                  'telesales (NL)',
    }
    found_labels = set()
    for kw, label in sales_keywords.items():
        if kw in text_lower and label not in found_labels:
            parsed['sales_signals'].append(label)
            found_labels.add(label)

    # Remote / freelance / commission signals
    remote_kw = [
        'remote', 'freelance', 'zzp', 'zelfstandig', 'commission only',
        'op commissie', 'provisie', 'no cure no pay', 'thuiswerk',
        'work from home', 'hybride', 'flexibel',
    ]
    for kw in remote_kw:
        if kw in text_lower:
            parsed['remote_signals'].append(kw)

    # Proof / quantified results
    import re as _re
    if _re.search(r'\d+\s*[%x×]\s*|\d+\s*(?:afspraken|deals|appointments|klanten|opdrachtgevers|omzet|revenue)', text_lower):
        parsed['has_proof'] = True
    if _re.search(r'(?:behaald|gerealiseerd|gescoord|closed|booked)\s+\d+', text_lower):
        parsed['has_proof'] = True

    # Red flags
    student_kw = ['student', 'studerend', 'afstuderen', 'stage', 'internship', 'bijbaan']
    for kw in student_kw:
        if kw in text_lower:
            parsed['red_flags'].append(f'student/education: "{kw}"')

    vague_kw = ['motivated', 'enthusiastic', 'hardworking', 'eager to learn',
                'team player', 'gemotiveerd', 'enthousiast', 'hands-on',
                'bereid om te leren', 'leergierig', 'proactief']
    vague_count = sum(1 for v in vague_kw if v in text_lower)
    if vague_count >= 2:
        parsed['red_flags'].append('vague profile (buzzwords, no concrete experience)')

    if not parsed['sales_signals'] and len(text_lower.strip()) > 30:
        parsed['red_flags'].append('no sales or cold calling signals detected')

    return parsed


def _score_source(parsed: dict) -> tuple:
    """
    Returns (score: int 0-100, tier: str, reasons: list[str], recommended_action: str)
    Pure arithmetic — no API calls.
    """
    score = 0
    reasons = []

    # Dutch language signals → +30
    if parsed.get('language_signals'):
        score += 30
        reasons.append('+30 Dutch language signals detected')
    elif parsed.get('location') in ('nederland', 'netherlands', 'holland', 'nl',
                                    'amsterdam', 'rotterdam', 'den haag', 'the hague',
                                    'utrecht', 'eindhoven', 'groningen'):
        score += 10
        reasons.append('+10 Located in Netherlands')

    # Cold calling / appointment setting → +25
    cold_labels = {'cold calling', 'appointment setting', 'cold calling (nl)', 'telesales', 'telesales (nl)'}
    if cold_labels & set(parsed.get('sales_signals', [])):
        score += 25
        reasons.append('+25 Cold calling / appointment setting experience')

    # B2B → +20
    b2b_labels = {'B2B sales', 'business development', 'account management', 'outbound sales', 'inside sales'}
    if b2b_labels & set(parsed.get('sales_signals', [])):
        score += 20
        reasons.append('+20 B2B / business development experience')

    # Closer / high-ticket / recruitment → +15
    premium_labels = {'sales closer', 'high-ticket sales', 'recruitment/staffing'}
    if premium_labels & set(parsed.get('sales_signals', [])):
        score += 15
        reasons.append('+15 Closer / high-ticket / recruitment experience')

    # General sales without above specifics → +5
    general_labels = {'general sales', 'sales (nl)', 'sales rep (nl)', 'commercial (nl)',
                      'lead generation', 'field sales', 'outdoor/field sales',
                      'door-to-door', 'door-to-door (nl)'}
    if general_labels & set(parsed.get('sales_signals', [])):
        score += 5
        reasons.append('+5 General sales experience')

    # Remote / freelance / commission → +10
    if parsed.get('remote_signals'):
        score += 10
        reasons.append('+10 Remote / freelance / commission signal')

    # Proof / quantified results → +10
    if parsed.get('has_proof'):
        score += 10
        reasons.append('+10 Quantified results / proof of performance')

    # Deductions
    if not parsed.get('sales_signals'):
        score -= 25
        reasons.append('-25 No sales or cold calling signals detected')

    student_flags = [f for f in parsed.get('red_flags', []) if 'student' in f]
    if student_flags:
        score -= 10
        reasons.append('-10 Student / education signal detected')

    vague_flags = [f for f in parsed.get('red_flags', []) if 'vague' in f]
    if vague_flags:
        score -= 10
        reasons.append('-10 Vague profile — only buzzwords, no concrete experience')

    score = max(0, min(100, score))

    if score >= 75:
        tier = 'A'
        action = 'Strong signal — approve and move to candidate pipeline immediately.'
    elif score >= 55:
        tier = 'B'
        action = 'Good signal — review profile manually and approve if satisfied.'
    elif score >= 35:
        tier = 'Nurture'
        action = 'Weak signal — gather more info or check back in 2–4 weeks.'
    else:
        tier = 'Reject'
        action = 'Insufficient sales signals — reject unless you have extra context.'

    return score, tier, reasons, action


def create_source_entry(data: dict) -> int:
    """Create a new source queue entry. Runs parse + score automatically."""
    raw_text = data.get('raw_profile_text', '') or ''
    parsed   = _parse_source_profile(raw_text)
    score, tier, reasons, action = _score_source(parsed)

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO candidate_source_queue
            (name, source_type, profile_url, raw_profile_text,
             parsed_json, score, tier, reasons_json, recommended_action,
             notes, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,'queued',?,?)
    """, (
        data.get('name', 'Unknown'),
        data.get('source_type', 'Manual'),
        data.get('profile_url') or None,
        raw_text or None,
        json.dumps(parsed),
        score,
        tier,
        json.dumps(reasons),
        action,
        data.get('notes') or None,
        now(), now(),
    ))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_source_entry(sid: int) -> dict:
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM candidate_source_queue WHERE id=?", (sid,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = to_dict(row)
    # Decode JSON fields
    try:
        d['parsed']  = json.loads(d['parsed_json'] or '{}')
    except Exception:
        d['parsed']  = {}
    try:
        d['reasons'] = json.loads(d['reasons_json'] or '[]')
    except Exception:
        d['reasons'] = []
    return d


def get_source_entries(status: str = '', tier: str = '', source_type: str = '') -> list:
    conn  = get_db()
    where = []
    args  = []
    if status:
        where.append("status=?"); args.append(status)
    if tier:
        where.append("tier=?"); args.append(tier)
    if source_type:
        where.append("source_type=?"); args.append(source_type)
    sql = "SELECT * FROM candidate_source_queue"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY score DESC, created_at DESC"
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = to_dict(r)
        try:
            d['reasons'] = json.loads(d['reasons_json'] or '[]')
        except Exception:
            d['reasons'] = []
        result.append(d)
    return result


def get_source_summary() -> dict:
    conn = get_db()
    def _c(sql, *args):
        try: return conn.execute(sql, args).fetchone()[0]
        except Exception: return 0
    s = {
        'total':   _c("SELECT COUNT(*) FROM candidate_source_queue"),
        'queued':  _c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='queued'"),
        'approved':_c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='approved'"),
        'rejected':_c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='rejected'"),
        'converted':_c("SELECT COUNT(*) FROM candidate_source_queue WHERE status='converted'"),
        'tier_a':  _c("SELECT COUNT(*) FROM candidate_source_queue WHERE tier='A' AND status='queued'"),
        'tier_b':  _c("SELECT COUNT(*) FROM candidate_source_queue WHERE tier='B' AND status='queued'"),
        'tier_nurture': _c("SELECT COUNT(*) FROM candidate_source_queue WHERE tier='Nurture' AND status='queued'"),
        'tier_reject':  _c("SELECT COUNT(*) FROM candidate_source_queue WHERE tier='Reject'  AND status='queued'"),
    }
    conn.close()
    return s


def rescore_source(sid: int) -> dict:
    """Re-parse and re-score an existing entry (e.g. after editing raw text)."""
    conn = get_db()
    row  = conn.execute(
        "SELECT raw_profile_text FROM candidate_source_queue WHERE id=?", (sid,)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Not found'}
    raw_text = row[0] or ''
    parsed   = _parse_source_profile(raw_text)
    score, tier, reasons, action = _score_source(parsed)
    conn.execute("""
        UPDATE candidate_source_queue
        SET parsed_json=?, score=?, tier=?, reasons_json=?, recommended_action=?, updated_at=?
        WHERE id=?
    """, (json.dumps(parsed), score, tier, json.dumps(reasons), action, now(), sid))
    conn.commit()
    conn.close()
    return {'ok': True, 'score': score, 'tier': tier}


def approve_source(sid: int) -> dict:
    """
    Approve a source entry.
    Creates a cold_caller_candidate from the source data.
    Returns {'ok': True, 'candidate_id': N}.
    """
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM candidate_source_queue WHERE id=?", (sid,)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Not found'}
    src = to_dict(row)
    if src['status'] in ('approved', 'converted'):
        conn.close()
        return {'ok': False, 'error': 'Already approved'}

    # Parse stored signals to fill candidate fields
    try:
        parsed = json.loads(src.get('parsed_json') or '{}')
    except Exception:
        parsed = {}

    # Map source fields → candidate fields
    sales_sigs = parsed.get('sales_signals', [])

    def _has(*labels):
        return any(any(l in s for s in sales_sigs) for l in labels)

    cold_exp   = ', '.join([s for s in sales_sigs if 'cold' in s or 'appointment' in s or 'tele' in s]) or None
    b2b_exp    = ', '.join([s for s in sales_sigs if 'B2B' in s or 'business' in s.lower() or 'account' in s]) or None
    close_exp  = ', '.join([s for s in sales_sigs if 'closer' in s or 'high-ticket' in s]) or None
    proof      = 'Quantified results mentioned' if parsed.get('has_proof') else None

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cold_caller_candidates
            (full_name, profile_url, platform_source, current_role,
             cold_calling_experience, b2b_experience, past_sales_roles,
             proof_results, language_level, commission_only_fit,
             notes, global_score, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'found',?,?)
    """, (
        src['name'],
        src.get('profile_url') or None,
        src.get('source_type', 'Manual'),
        parsed.get('role') or None,
        cold_exp,
        b2b_exp,
        ', '.join([s for s in sales_sigs if s not in (cold_exp or '') and s not in (b2b_exp or '')]) or None,
        proof,
        'NL' if parsed.get('language_signals') or parsed.get('location') else None,
        1 if parsed.get('remote_signals') else 0,
        src.get('notes') or None,
        src.get('score', 0),
        now(), now(),
    ))
    conn.commit()
    candidate_id = cur.lastrowid

    # Mark source as converted
    conn.execute("""
        UPDATE candidate_source_queue
        SET status='converted', candidate_id=?, updated_at=?
        WHERE id=?
    """, (candidate_id, now(), sid))
    conn.commit()

    # Create a "Review Approved Source" action task
    try:
        create_action_task({
            'task_type':    'Review Candidate',
            'title':        f'Review approved source — {src["name"]}',
            'description':  f'Source approved from {src.get("source_type","Manual")}. Candidate created. Score: {src.get("score",0)} ({src.get("tier","?")}).',
            'priority':     'High' if src.get('tier') == 'A' else 'Medium',
            'status':       'Pending',
            'owner':        'Rutger',
            'related_type': 'candidate',
            'related_id':   candidate_id,
            'related_name': src['name'],
        })
    except Exception:
        pass

    conn.close()
    return {'ok': True, 'candidate_id': candidate_id}


def reject_source(sid: int, reason: str = '') -> dict:
    conn = get_db()
    conn.execute("""
        UPDATE candidate_source_queue
        SET status='rejected',
            notes=CASE WHEN notes IS NULL THEN ? ELSE notes||' | Reject: '||? END,
            updated_at=?
        WHERE id=?
    """, (f'Rejected: {reason}' if reason else 'Rejected', reason or '', now(), sid))
    conn.commit()
    conn.close()
    return {'ok': True}
