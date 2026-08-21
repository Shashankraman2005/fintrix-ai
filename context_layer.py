import sqlite3, json, logging, re
from datetime import datetime, timezone
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] context_layer: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)

_DDL_APPLICANT_CARDS = '''CREATE TABLE IF NOT EXISTS applicant_cards (id INTEGER PRIMARY KEY AUTOINCREMENT, applicant_id TEXT NOT NULL UNIQUE, name TEXT, city TEXT, business_type TEXT, grade TEXT NOT NULL, outcome TEXT NOT NULL, default_probability REAL NOT NULL, decision_source TEXT DEFAULT 'model', primary_reason TEXT, pre_layer_rule TEXT, manager_remarks TEXT, is_deleted INTEGER NOT NULL DEFAULT 0, score_date TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);'''
_DDL_APPLICANT_FEATURES = '''CREATE TABLE IF NOT EXISTS applicant_features (id INTEGER PRIMARY KEY AUTOINCREMENT, applicant_id TEXT NOT NULL REFERENCES applicant_cards(applicant_id) ON DELETE CASCADE, feature_name TEXT NOT NULL, feature_value REAL, updated_at TEXT NOT NULL, UNIQUE(applicant_id, feature_name));'''
_DDL_APPLICANT_SHAP = '''CREATE TABLE IF NOT EXISTS applicant_shap_explanations (id INTEGER PRIMARY KEY AUTOINCREMENT, applicant_id TEXT NOT NULL REFERENCES applicant_cards(applicant_id) ON DELETE CASCADE, rank INTEGER NOT NULL, feature TEXT NOT NULL, reason TEXT, shap_value REAL, direction TEXT, impact TEXT, updated_at TEXT NOT NULL, UNIQUE(applicant_id, rank));'''
_DDL_APPLICANT_LOAN_OFFERS = '''CREATE TABLE IF NOT EXISTS applicant_loan_offers (id INTEGER PRIMARY KEY AUTOINCREMENT, applicant_id TEXT NOT NULL REFERENCES applicant_cards(applicant_id) ON DELETE CASCADE UNIQUE, eligible INTEGER NOT NULL DEFAULT 0, interest_rate_min REAL, interest_rate_max REAL, max_loan_amount REAL, tenure_options_json TEXT, recommended_product TEXT, alternative_products_json TEXT, updated_at TEXT NOT NULL);'''
_DDL_INDEXES = ['CREATE INDEX IF NOT EXISTS idx_cards_grade ON applicant_cards(grade);','CREATE INDEX IF NOT EXISTS idx_cards_outcome ON applicant_cards(outcome);','CREATE INDEX IF NOT EXISTS idx_cards_score_date ON applicant_cards(score_date);','CREATE INDEX IF NOT EXISTS idx_cards_deleted ON applicant_cards(is_deleted);','CREATE INDEX IF NOT EXISTS idx_features_appid ON applicant_features(applicant_id);','CREATE INDEX IF NOT EXISTS idx_shap_appid ON applicant_shap_explanations(applicant_id);']

def _now(): return datetime.now(timezone.utc).isoformat()
def _validate_applicant_id(applicant_id):
    if not applicant_id or not isinstance(applicant_id, str): raise ValueError('applicant_id must be non-empty string')
    if len(applicant_id) > 128: raise ValueError('applicant_id too long')
    if not re.match(r'^[\w\-\.]+$', applicant_id): raise ValueError(f'Invalid chars in applicant_id: {applicant_id}')
def _connect(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False); conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;'); conn.execute('PRAGMA journal_mode = WAL;'); return conn
def _safe_float(value, default=0.0):
    try: return float(value) if value is not None else default
    except: return default
def _safe_str(value, default=''):
    return str(value) if value is not None else default

def init_database(db_path):
    log.info('Initialising database at: %s', db_path)
    with _connect(db_path) as conn:
        conn.execute(_DDL_APPLICANT_CARDS); conn.execute(_DDL_APPLICANT_FEATURES)
        conn.execute(_DDL_APPLICANT_SHAP); conn.execute(_DDL_APPLICANT_LOAN_OFFERS)
        for idx in _DDL_INDEXES: conn.execute(idx)
        try:
            conn.execute("ALTER TABLE applicant_cards ADD COLUMN manager_remarks TEXT;")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    log.info('Database initialised.')

def save_applicant_card(db_path, scoring_result, applicant_id, name='', city='', business_type=''):
    _validate_applicant_id(applicant_id); now = _now()
    score_date = scoring_result.get('scored_at') or now
    grade = _safe_str(scoring_result.get('grade'), '?')
    outcome = _safe_str(scoring_result.get('outcome') or scoring_result.get('decision'), 'UNKNOWN')
    default_prob = _safe_float(scoring_result.get('default_probability'))
    decision_src = _safe_str(scoring_result.get('decision_source'), 'model')
    primary_reason = _safe_str(scoring_result.get('primary_reason'))
    pld = scoring_result.get('pre_layer_decision')
    pre_layer_rule = _safe_str(pld.get('rule') if isinstance(pld, dict) else pld)
    loan_offer_raw = scoring_result.get('loan_offer') or {}
    eligible = int(bool(loan_offer_raw.get('eligible', False)))
    ir_min = _safe_float(loan_offer_raw.get('interest_rate_min'))
    ir_max = _safe_float(loan_offer_raw.get('interest_rate_max'))
    max_loan = _safe_float(loan_offer_raw.get('max_loan_amount'))
    tenures_json = json.dumps(loan_offer_raw.get('tenure_options_months') or [])
    rec_product = _safe_str(loan_offer_raw.get('recommended_product'))
    alt_products = scoring_result.get('alternative_products') or loan_offer_raw.get('alternative_products') or []
    alt_json = json.dumps(alt_products)
    shap_rows = scoring_result.get('shap_reasons') or scoring_result.get('shap_explanations') or []
    features_dict = scoring_result.get('features') or {}
    log.info('Saving applicant card: %s (%s, %s)', applicant_id, name, grade)
    with _connect(db_path) as conn:
        conn.execute('''INSERT INTO applicant_cards (applicant_id,name,city,business_type,grade,outcome,default_probability,decision_source,primary_reason,pre_layer_rule,score_date,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(applicant_id) DO UPDATE SET name=excluded.name,city=excluded.city,business_type=excluded.business_type,grade=excluded.grade,outcome=excluded.outcome,default_probability=excluded.default_probability,decision_source=excluded.decision_source,primary_reason=excluded.primary_reason,pre_layer_rule=excluded.pre_layer_rule,score_date=excluded.score_date,updated_at=excluded.updated_at''', (applicant_id,name,city,business_type,grade,outcome,default_prob,decision_src,primary_reason,pre_layer_rule,score_date,now,now))
        conn.execute('''INSERT INTO applicant_loan_offers (applicant_id,eligible,interest_rate_min,interest_rate_max,max_loan_amount,tenure_options_json,recommended_product,alternative_products_json,updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(applicant_id) DO UPDATE SET eligible=excluded.eligible,interest_rate_min=excluded.interest_rate_min,interest_rate_max=excluded.interest_rate_max,max_loan_amount=excluded.max_loan_amount,tenure_options_json=excluded.tenure_options_json,recommended_product=excluded.recommended_product,alternative_products_json=excluded.alternative_products_json,updated_at=excluded.updated_at''', (applicant_id,eligible,ir_min,ir_max,max_loan,tenures_json,rec_product,alt_json,now))
        for rank, factor in enumerate(shap_rows[:5], start=1):
            conn.execute('''INSERT INTO applicant_shap_explanations (applicant_id,rank,feature,reason,shap_value,direction,impact,updated_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(applicant_id,rank) DO UPDATE SET feature=excluded.feature,reason=excluded.reason,shap_value=excluded.shap_value,direction=excluded.direction,impact=excluded.impact,updated_at=excluded.updated_at''', (applicant_id,rank,_safe_str(factor.get('feature')),_safe_str(factor.get('reason')),_safe_float(factor.get('shap_value')),_safe_str(factor.get('direction')),_safe_str(factor.get('impact')),now))
        for feat_name, feat_val in features_dict.items():
            conn.execute('''INSERT INTO applicant_features (applicant_id,feature_name,feature_value,updated_at) VALUES (?,?,?,?) ON CONFLICT(applicant_id,feature_name) DO UPDATE SET feature_value=excluded.feature_value,updated_at=excluded.updated_at''', (applicant_id,feat_name,_safe_float(feat_val),now))
        conn.commit()
        row = conn.execute('SELECT id FROM applicant_cards WHERE applicant_id=?', (applicant_id,)).fetchone()
        card_id = row['id'] if row else -1
    log.info('Saved applicant card id=%d for %s', card_id, applicant_id)
    return card_id

def fetch_applicant_card(db_path, applicant_id):
    _validate_applicant_id(applicant_id)
    with _connect(db_path) as conn:
        card_row = conn.execute('SELECT * FROM applicant_cards WHERE applicant_id=? AND is_deleted=0', (applicant_id,)).fetchone()
        if card_row is None: log.warning('Applicant not found: %s', applicant_id); return None
        offer_row = conn.execute('SELECT * FROM applicant_loan_offers WHERE applicant_id=?', (applicant_id,)).fetchone()
        shap_rows = conn.execute('SELECT rank,feature,reason,shap_value,direction,impact FROM applicant_shap_explanations WHERE applicant_id=? ORDER BY rank', (applicant_id,)).fetchall()
        feat_rows = conn.execute('SELECT feature_name,feature_value FROM applicant_features WHERE applicant_id=?', (applicant_id,)).fetchall()
    loan_offer_out = {}; alt_products_out = []
    if offer_row:
        loan_offer_out = {'eligible': bool(offer_row['eligible']), 'interest_rate': f"{offer_row['interest_rate_min']}-{offer_row['interest_rate_max']}% p.a." if offer_row['interest_rate_min'] and offer_row['interest_rate_max'] else 'N/A', 'max_loan': offer_row['max_loan_amount'], 'tenures': json.loads(offer_row['tenure_options_json'] or '[]'), 'recommended_product': offer_row['recommended_product']}
        alt_products_out = json.loads(offer_row['alternative_products_json'] or '[]')
    return {'applicant_id': card_row['applicant_id'], 'name': card_row['name'], 'city': card_row['city'], 'business_type': card_row['business_type'], 'score_date': card_row['score_date'], 'grade': card_row['grade'], 'decision': card_row['outcome'], 'default_probability': card_row['default_probability'], 'decision_source': card_row['decision_source'], 'primary_reason': card_row['primary_reason'], 'manager_remarks': card_row['manager_remarks'], 'pre_layer_rule': card_row['pre_layer_rule'], 'top_shap_factors': [{'rank': r['rank'], 'feature': r['feature'], 'reason': r['reason'], 'shap_value': r['shap_value'], 'direction': r['direction'], 'impact': r['impact']} for r in shap_rows], 'all_features': {r['feature_name']: r['feature_value'] for r in feat_rows}, 'loan_offer': loan_offer_out, 'alternative_products': alt_products_out}

def search_applicants(db_path, filters):
    conditions = ['is_deleted=0']; params = []
    if 'grade' in filters: conditions.append('grade=?'); params.append(filters['grade'].upper())
    if 'decision' in filters: conditions.append('outcome=?'); params.append(filters['decision'].upper())
    if 'score_min' in filters: conditions.append('default_probability>=?'); params.append(float(filters['score_min']))
    if 'score_max' in filters: conditions.append('default_probability<=?'); params.append(float(filters['score_max']))
    if 'date_from' in filters: conditions.append('score_date>=?'); params.append(filters['date_from'])
    if 'date_to' in filters: conditions.append('score_date<=?'); params.append(filters['date_to'])
    for col in ('name','city','business_type'):
        if col in filters: conditions.append(f'{col} LIKE ?'); params.append(f'%{filters[col]}%')
    sql = f"SELECT applicant_id,name,city,business_type,grade,outcome,default_probability,primary_reason,manager_remarks,score_date FROM applicant_cards WHERE {' AND '.join(conditions)} ORDER BY score_date DESC"
    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [{'applicant_id': r['applicant_id'], 'name': r['name'], 'city': r['city'], 'business_type': r['business_type'], 'grade': r['grade'], 'decision': r['outcome'], 'default_probability': r['default_probability'], 'primary_reason': r['primary_reason'], 'manager_remarks': r['manager_remarks'], 'score_date': r['score_date']} for r in rows]

def update_applicant_status(db_path, applicant_id, outcome, remarks):
    _validate_applicant_id(applicant_id)
    with _connect(db_path) as conn:
        conn.execute("UPDATE applicant_cards SET outcome=?, manager_remarks=?, updated_at=? WHERE applicant_id=?", 
                     (outcome, remarks, _now(), applicant_id))
        conn.commit()

def fetch_applicant_status(db_path, applicant_id):
    _validate_applicant_id(applicant_id)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT applicant_id, name, grade, outcome, primary_reason, manager_remarks, score_date FROM applicant_cards WHERE applicant_id=? AND is_deleted=0", (applicant_id,)).fetchone()
        if not row: return None
        return dict(row)

def delete_applicant_card(db_path, applicant_id):
    _validate_applicant_id(applicant_id); now = _now()
    with _connect(db_path) as conn:
        cursor = conn.execute('UPDATE applicant_cards SET is_deleted=1,updated_at=? WHERE applicant_id=? AND is_deleted=0', (now, applicant_id)); conn.commit()
    deleted = cursor.rowcount > 0
    if deleted: log.info('Soft-deleted: %s', applicant_id)
    return deleted

def bulk_save_applicant_cards(db_path, records):
    ids = []
    for rec in records:
        ids.append(save_applicant_card(db_path, rec['scoring_result'], rec['applicant_id'], rec.get('name',''), rec.get('city',''), rec.get('business_type','')))
    return ids

def get_grade_distribution(db_path):
    with _connect(db_path) as conn:
        rows = conn.execute('SELECT grade,outcome,COUNT(*) as cnt FROM applicant_cards WHERE is_deleted=0 GROUP BY grade,outcome ORDER BY grade').fetchall()
    return {f"{r['grade']} ({r['outcome']})": r['cnt'] for r in rows}
