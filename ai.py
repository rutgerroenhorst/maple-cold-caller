"""
Maple Cold Caller — AI Layer (Anthropic API, stdlib only)
Requires: ANTHROPIC_API_KEY env var
Model: claude-haiku-4-5  (fast + cheap for recruitment ops)
"""
import http.client
import json
import os
import re

MODEL = "claude-haiku-4-5-20251001"
API_HOST = "api.anthropic.com"
API_VERSION = "2023-06-01"


# ──────────────────────────────────────────────────────────────────────────────
# Core API call
# ──────────────────────────────────────────────────────────────────────────────

def call_claude(user_prompt: str, system: str = "", max_tokens: int = 1024):
    """
    Call Anthropic Messages API via stdlib http.client.
    Returns (text, error_string). One of the two will be None.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None, "ANTHROPIC_API_KEY not set — add it to your environment and restart the server."

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system or "You are a cold-calling recruitment expert. Always respond with valid JSON only, no markdown fences.",
        "messages": [{"role": "user", "content": user_prompt}]
    }).encode()

    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
        "content-length": str(len(payload)),
    }

    try:
        conn = http.client.HTTPSConnection(API_HOST, timeout=30)
        conn.request("POST", "/v1/messages", payload, headers)
        resp = conn.getresponse()
        body = resp.read().decode()
        data = json.loads(body)
        if resp.status == 200:
            text = data["content"][0]["text"].strip()
            # Strip markdown fences if model forgets
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text.strip())
            return text, None
        else:
            msg = data.get("error", {}).get("message", f"HTTP {resp.status}")
            return None, msg
    except Exception as e:
        return None, str(e)
    finally:
        try: conn.close()
        except: pass


def parse_json(text):
    """Parse JSON from API response, return (dict, error)."""
    try:
        return json.loads(text), None
    except Exception as e:
        return None, f"JSON parse error: {e} — raw: {text[:200]}"


# ──────────────────────────────────────────────────────────────────────────────
# 1. Candidate Scoring
# ──────────────────────────────────────────────────────────────────────────────

SCORE_CANDIDATE_SYSTEM = """You are a senior cold-calling recruitment expert at Maple.
Your job is to assess whether a candidate is strong for cold calling / appointment setting roles.
Always respond with valid JSON only — no markdown, no explanation outside the JSON."""

def score_candidate(candidate: dict) -> tuple:
    """
    Returns (result_dict, error).
    result_dict keys: score (0-100), summary, strengths, weaknesses, verdict
    """
    prompt = f"""Score this cold calling candidate from 0 to 100.

CANDIDATE PROFILE:
- Name: {candidate.get('full_name', '')}
- Current Role: {candidate.get('current_role', 'Unknown')}
- Past Sales Roles: {candidate.get('past_sales_roles', 'Not provided')}
- Cold Calling Experience: {candidate.get('cold_calling_experience', 'Not provided')}
- Appointment Setting Experience: {candidate.get('appointment_setting_experience', 'Not provided')}
- D2D (Door to Door) Experience: {candidate.get('d2d_experience', 'Not provided')}
- B2B Experience: {candidate.get('b2b_experience', 'Not provided')}
- Gatekeeper Experience: {candidate.get('gatekeeper_experience', 'Not provided')}
- Language Level: {candidate.get('language_level', 'Unknown')}
- Availability: {candidate.get('availability', 'Unknown')}
- Commission-Only Fit: {'Yes' if candidate.get('commission_only_fit') else 'No'}
- Proof / Results: {candidate.get('proof_results', 'None provided')}
- Notes: {candidate.get('notes', '')}
- Platform Source: {candidate.get('platform_source', '')}

Scoring criteria:
- 80-100: Proven cold caller with real appointment setting numbers, B2B experience, gatekeeper skills
- 60-79: Good background, some cold calling, trainable with solid sales instincts
- 40-59: Limited direct experience but transferable skills
- 20-39: Mostly inbound or account management, weak cold outbound background
- 0-19: No relevant experience

Respond with ONLY this JSON (no markdown):
{{
  "score": <integer 0-100>,
  "summary": "<2 sentences max — direct assessment>",
  "strengths": "<bullet list of up to 3 key strengths>",
  "weaknesses": "<bullet list of up to 3 key concerns>",
  "verdict": "<one of: Strong Hire | Good Fit | Maybe | Weak | Pass>"
}}"""

    text, err = call_claude(prompt, SCORE_CANDIDATE_SYSTEM, max_tokens=512)
    if err:
        return None, err
    return parse_json(text)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Campaign Match Scoring
# ──────────────────────────────────────────────────────────────────────────────

SCORE_MATCH_SYSTEM = """You are a cold-calling recruitment expert at Maple.
Evaluate how well a candidate matches a specific client campaign's requirements.
Always respond with valid JSON only."""

def score_match(candidate: dict, campaign: dict, profile: dict = None) -> tuple:
    """
    Returns (result_dict, error).
    result_dict keys: match_score, fit_summary, strengths, risks,
                      recommended_next_action, reject_reason
    """
    profile_section = ""
    if profile:
        profile_section = f"""
IDEAL CALLER PROFILE FOR THIS CAMPAIGN:
- Must-Have Skills: {profile.get('must_have_skills', '')}
- Nice-to-Have: {profile.get('nice_to_have_skills', '')}
- Red Flags: {profile.get('red_flags', '')}
- Outreach Angle: {profile.get('outreach_angle', '')}
"""

    prompt = f"""Score the match between this candidate and client campaign (0-100).

CAMPAIGN:
- Client: {campaign.get('client_name', '')}
- Niche: {campaign.get('niche', '')}
- Offer: {campaign.get('offer_description', '')}
- Target Market: {campaign.get('target_market', '')}
- Type: {campaign.get('b2b_or_b2c', '')}
- Language Required: {campaign.get('language_required', '')}
- Timezone: {campaign.get('country_timezone', '')}
- Pay: {campaign.get('pay_structure', '')} / {campaign.get('appointment_payout', '')} per appt
- Gatekeeper Difficulty: {campaign.get('gatekeeper_difficulty', '')}
- Required Experience: {campaign.get('required_experience', '')}
- Preferred Traits: {campaign.get('preferred_traits', '')}
- Disqualifiers: {campaign.get('disqualifiers', '')}
{profile_section}
CANDIDATE:
- Name: {candidate.get('full_name', '')}
- Current Role: {candidate.get('current_role', '')}
- Cold Calling XP: {candidate.get('cold_calling_experience', '')}
- Appointment Setting: {candidate.get('appointment_setting_experience', '')}
- B2B XP: {candidate.get('b2b_experience', '')}
- Gatekeeper XP: {candidate.get('gatekeeper_experience', '')}
- Language: {candidate.get('language_level', '')}
- Commission-Only Fit: {'Yes' if candidate.get('commission_only_fit') else 'No'}
- Proof/Results: {candidate.get('proof_results', '')}

Respond with ONLY this JSON:
{{
  "match_score": <integer 0-100>,
  "fit_summary": "<1-2 sentences on overall fit>",
  "strengths": "<3 bullet points of why this candidate fits>",
  "risks": "<3 bullet points of risks or gaps>",
  "recommended_next_action": "<specific next step: Send DM / Book intro call / Skip / etc.>",
  "reject_reason": "<if match_score < 40, explain why to reject — else empty string>"
}}"""

    text, err = call_claude(prompt, SCORE_MATCH_SYSTEM, max_tokens=600)
    if err:
        return None, err
    return parse_json(text)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Outreach Message Generator
# ──────────────────────────────────────────────────────────────────────────────

OUTREACH_SYSTEM = """You are a cold outreach copywriter at Maple — a cold calling recruitment firm.
Write natural, non-cringe DMs for recruiting cold callers.
Tone: confident, brief, direct — like a recruiter who knows what they want.
Always respond with valid JSON only."""

def generate_outreach(candidate: dict, campaign: dict, profile: dict = None) -> tuple:
    """
    Returns (result_dict, error).
    result_dict keys: connection_request, first_dm, follow_up_1, follow_up_2,
                      qualification_questions, booking_message
    """
    profile_angle = profile.get('outreach_angle', '') if profile else ''

    prompt = f"""Write 6 outreach messages to recruit this candidate for this cold calling role.

CANDIDATE:
- Name: {candidate.get('full_name', '')}
- Current Role: {candidate.get('current_role', 'Sales professional')}
- Platform: {candidate.get('platform_source', 'LinkedIn')}
- Experience: {candidate.get('cold_calling_experience', '')}

CAMPAIGN / ROLE:
- Client Niche: {campaign.get('niche', '')}
- Target Market: {campaign.get('target_market', '')}
- Type: {campaign.get('b2b_or_b2c', 'B2B')}
- Pay: {campaign.get('pay_structure', 'Commission-based')}
- Appointment Payout: {campaign.get('appointment_payout', '')}
- Closed Deal Bonus: {campaign.get('closed_deal_bonus', '')}
- Language: {campaign.get('language_required', 'English')}
- Preferred Traits: {campaign.get('preferred_traits', '')}

OUTREACH ANGLE: {profile_angle or 'Lead with earning potential and flexible schedule'}

Rules:
- connection_request: Max 280 chars, no "I'd like to add you" opener
- first_dm: 3-5 lines, personalised, clear hook
- follow_up_1: 2-3 lines, add urgency or social proof
- follow_up_2: 1-2 lines, last touch, easy out
- qualification_questions: 3-4 numbered questions to pre-qualify
- booking_message: 2-3 lines to book a 15-min call, include [CALENDAR_LINK] placeholder
- Use {{first_name}} placeholder where appropriate

Respond with ONLY this JSON:
{{
  "connection_request": "...",
  "first_dm": "...",
  "follow_up_1": "...",
  "follow_up_2": "...",
  "qualification_questions": "...",
  "booking_message": "..."
}}"""

    text, err = call_claude(prompt, OUTREACH_SYSTEM, max_tokens=1200)
    if err:
        return None, err
    return parse_json(text)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Bulk AI Scoring helper
# ──────────────────────────────────────────────────────────────────────────────

def bulk_score_candidates(candidates: list) -> list:
    """
    Score a list of candidates. Returns list of (candidate_id, result_or_None, error_or_None).
    """
    results = []
    for c in candidates:
        result, err = score_candidate(c)
        results.append((c['id'], result, err))
    return results
