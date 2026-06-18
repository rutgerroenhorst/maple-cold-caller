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
            missions = to_list(conn.execute(
                "SELECT * FROM search_missions WHERE status='active'").fetchall())
            total = conn.execute(
                "SELECT COUNT(*) FROM cold_caller_candidates").fetchone()[0]
            if missions:
                output = f"Active search missions: {len(missions)}\n\n"
                for m in missions:
                    kws = [k.strip() for k in (m.get('keywords') or '').split('\n') if k.strip()][:3]
                    output += f"▸ {m['name']} — target: {m.get('target_role') or 'any'}, daily target: {m['daily_target']}/day\n"
                    if kws:
                        q_str = '" OR "'.join(kws[:2])
                        output += f'  Recommended query: site:linkedin.com/in ("{q_str}") {m.get("target_market","Netherlands")}\n'
                    output += '\n'
                output += f"Total candidates in pipeline: {total}"
            else:
                output = f"No active search missions found. Total candidates: {total}\nCreate a search mission first to guide sourcing."
                issue = "No active search missions"
                recommendation = "Create at least one search mission to direct candidate sourcing"

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
            from datetime import datetime as _dt
            today = _dt.utcnow().strftime('%Y-%m-%d')
            due = to_list(conn.execute(
                """SELECT oq.next_follow_up_date, oq.outreach_status, ca.full_name
                   FROM outreach_queue oq
                   LEFT JOIN cold_caller_candidates ca ON oq.candidate_id=ca.id
                   WHERE oq.outreach_status NOT IN ('closed','booked')
                     AND (oq.next_follow_up_date <= ? OR oq.next_follow_up_date IS NULL
                          OR oq.next_follow_up_date='')
                   LIMIT 10""", (today,)).fetchall())
            interviews = to_list(conn.execute(
                """SELECT iq.interview_time, ca.full_name
                   FROM interview_queue iq
                   LEFT JOIN cold_caller_candidates ca ON iq.candidate_id=ca.id
                   WHERE iq.interview_date=? AND iq.status='scheduled'""", (today,)).fetchall())
            if due:
                output = f"{len(due)} outreach item(s) need follow-up:\n"
                for o in due[:5]:
                    output += f"  ▸ {o.get('full_name','?')} — {o.get('outreach_status','?')} — due: {o.get('next_follow_up_date','—')}\n"
                issue = f"{len(due)} overdue follow-ups"
                recommendation = f"Send follow-up messages to {len(due)} overdue candidate(s)"
            else:
                output = "No overdue outreach items.\n"
            if interviews:
                output += f"\n{len(interviews)} interview(s) scheduled today:\n"
                for i in interviews:
                    output += f"  ▸ {i.get('full_name','?')} at {i.get('interview_time','TBD')}\n"
            else:
                output += "No interviews today."
            if not due and not interviews:
                recommendation = "Pipeline clear — keep sourcing new candidates."

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

            if nc == 0:
                bot, impact = "No candidates in pipeline", "Critical"
                rec = "Add at least 5 candidates before any other work"
                fix = "Go to /candidates/new or run a search mission and paste profiles"
            elif ncamp == 0:
                bot, impact = "No active campaigns", "High"
                rec = "Create a campaign to enable candidate matching"
                fix = "Go to /campaigns/new and create a campaign"
            elif nmiss == 0:
                bot, impact = "No active search missions", "Medium"
                rec = "Create a search mission to direct the Candidate Research Worker"
                fix = "Go to /search-missions/new"
            elif ndue > 0:
                bot = f"{ndue} overdue follow-up(s)"
                impact = "Medium"
                rec = f"Action {ndue} overdue follow-up(s) before candidates go cold"
                fix = "Go to /outreach and follow up with overdue items"
            elif nout == 0 and nc > 0:
                bot, impact = "No outreach initiated", "Medium"
                rec = "Start outreach on your top candidates"
                fix = "Go to /candidates → pick top scored → Add Outreach → Generate with AI"
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
