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
            rs = get_research_summary()
            missions = to_list(conn.execute(
                "SELECT * FROM search_missions WHERE status='active'").fetchall())
            total_cands = conn.execute(
                "SELECT COUNT(*) FROM cold_caller_candidates").fetchone()[0]

            output = "Candidate Research Worker — Status\n\n"
            output += f"Active missions:       {rs['active_missions']}\n"
            output += f"Sources in inbox:      {rs['total_sources']} ({rs['unprocessed']} unprocessed)\n"
            output += f"Review queue:          {rs['queue_total']} total\n"
            output += f"  • New:               {rs['queue_new']}\n"
            output += f"  • Approved:          {rs['queue_approved']}\n"
            output += f"  • Moved→Candidates:  {rs['moved_to_candidates']}\n"
            output += f"  • Rejected/Dupes:    {rs['queue_rejected'] + rs['queue_duplicate']}\n"
            output += f"Pipeline candidates:   {total_cands}\n\n"

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
                output += f"Top candidate in queue: {tc['name']} — score {tc['score']} ({tc['level']}) — {tc['best_role']}\n"

            # Set issue / recommendation
            if rs['unprocessed'] > 0:
                issue = f"{rs['unprocessed']} source(s) waiting to be processed"
                recommendation = "Go to /research/sources and click 'Process' on each unprocessed source"
            elif rs['queue_new'] > 0:
                issue = f"{rs['queue_new']} candidates in queue waiting for review"
                recommendation = "Go to /research/queue and approve or reject candidates"
            elif not missions:
                issue = "No active search missions"
                recommendation = "Create a search mission at /search-missions/new"
            else:
                issue = ""
                recommendation = "Generate new search queries at /research/queries and paste results into /research/sources"

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
