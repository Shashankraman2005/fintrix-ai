"""Pre-layer rule engine for PDR.
Three rule types in strict priority order:
  Type 1 - Hard rejection: unambiguous fraud or extreme stress
  Type 2 - Edge case protection: legitimate non-standard profiles
  Type 3 - Manual review: ambiguous signals for human judgment
Returns None if no rule fires - send to ML model.
"""

from typing import Optional

# ── Threshold constants with documented sources ──────────
# Sources:
#   RBI Master Direction - NBFC Systemically Important
#   TransUnion CIBIL MSME Credit Health Index 2023
#   NABARD Financial Inclusion Report 2023

# Hard rejection
T_P2P_BOUNCE_COMBO       = 3     # CIBIL: 3+ bounces with circular flow = fraud pattern
T_GST_VARIANCE_REJECT    = 1.5   # RBI: >150% declared-vs-actual = material misrepresentation
T_BOUNCE_HARD_REJECT     = 5     # CIBIL: 5+ annual bounces = chronic inability
T_MIN_BAL_VIOLATION      = 3     # RBI: 3+ min balance violations = severe liquidity failure
T_CASH_DEPENDENCY_HIGH   = 0.80  # NABARD: >80% cash = off-book obligations likely
T_CASH_BOUNCE_COMBO      = 3     # Same as T_P2P_BOUNCE_COMBO

# Edge case protection
T_TELECOM_VINTAGE_STRONG = 1000  # ~2.7 years — RBI identity stability benchmark
T_TELECOM_VINTAGE_MEDIUM = 500   # ~1.4 years — minimum identity continuity
T_TELECOM_VINTAGE_NEW_BIZ = 1500 # ~4.1 years — strong identity for new business
T_GST_SCORE_STRONG       = 6     # 6/10 returns filed — RBI compliance threshold
T_GST_SCORE_NEW_BIZ      = 2     # Minimum for new business (early stage allowance)
T_GST_VARIANCE_WARN      = 0.8   # >80% variance triggers review not rejection
T_CASH_DEPENDENCY_LOW    = 0.15  # <15% cash = digital-first borrower (CIBIL)
T_CASH_DEPENDENCY_MEDIUM = 0.20  # <20% cash = acceptable for NRI/platform
T_EMERGENCY_BUFFER_MIN   = 2.0   # RBI: 2 months buffer = minimum viable liquidity
T_UTILITY_CONSISTENCY    = 0.85  # >85% on-time utility = strong payment discipline
T_CUSTOMER_CONCENTRATION = 0.85  # >85% from 1-2 clients = single point failure
T_EOD_VOLATILITY         = 0.40  # >40% EOD variance = unstable cash management
T_BOUNCE_MODERATE        = 3     # 3-4 bounces = moderate stress signal
T_CASH_DEPENDENCY_MOD    = 0.10  # >10% cash with bounces = combined stress

# Seasonal
T_SEASONALITY_INDEX      = 0.60  # >60% in specific months = seasonal (RBI definition)
T_SEASONAL_GST_MIN       = 4     # Min GST filings for legitimate seasonal business

# Geographic
T_REGION_HIGH_RISK       = 3     # Tier 3 = elevated cluster default exposure
T_CLUSTER_CASHFLOW       = 0.50  # >50% cashflow volatility in high-risk region
T_CLUSTER_CONCENTRATION  = 0.60  # >60% customer concentration in cluster

# Income stress
T_INCOME_DROP_SEVERE     = -0.30 # >30% MoM decline = material income event (RBI: >25%)
T_INCOME_DROP_BUFFER     = 1.5   # <1.5 months buffer during drop = critical stress
T_INCOME_DROP_BOUNCES    = 1     # Any bounce during income drop = early warning

# First time borrower
T_NEW_BUSINESS_VINTAGE   = 6     # <=6 months = early stage MSME (RBI priority sector)
T_NEW_BIZ_GST_MIN        = 2     # Minimum GST compliance for new business
T_NEW_BIZ_BUFFER         = 1.0   # Minimum 1 month operating reserve

# NEW: Balance inflation
T_BALANCE_INFLATION_VOL  = 0.85  # >85% EOD volatility = extreme swings
T_NEW_SIM_DAYS           = 120   # <120 days = very new SIM
T_MIN_SIGNAL_THRESHOLD   = 0.10  # Minimum signal coverage to avoid zero-profile

# Demographic risk thresholds (used in Type 2/3 rules)
T_AGE_YOUNG              = 26    # <26 years = elevated default risk (RBI youth segment)
T_AGE_SENIOR             = 55    # >55 years = stable income / pensioner segment
T_HIGH_INCOME_RISK       = 4     # income_type_risk_score >= 4 = unemployed/maternity
T_CRITICAL_INCOME_RISK   = 5     # income_type_risk_score == 5 = unemployed (highest risk)
T_FAMILY_BURDEN_HIGH     = 0.50  # >50% children/family = high obligation ratio
T_CONTACT_POOR           = 1     # contactability_score <= 1 = hard to verify


def apply_pre_layer(features: dict) -> Optional[tuple]:
    # ── TYPE 1: HARD REJECTION ──

    # Seasonal business protection — must check BEFORE GST variance rejection
    # A seasonal spike with consistent GST filing is legitimate, not fraud
    if (features.get('revenue_seasonality_index', 0) > T_SEASONALITY_INDEX and
        features.get('gst_filing_consistency_score', 0) >= T_SEASONAL_GST_MIN and
        features.get('gst_to_bank_variance', 0) > T_GST_VARIANCE_REJECT and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('p2p_circular_loop_flag', 0) == 0):
        return ('C', 'MANUAL REVIEW',
                'Seasonal revenue spike detected with consistent GST filing history - '
                'revenue concentration in specific months is consistent with seasonal '
                'business patterns. Verify spike is tied to known seasonal event.')

    # Circular fund flow with bounces
    if (features.get('p2p_circular_loop_flag', 0) == 1 and
        features.get('bounced_transaction_count', 0) >= T_P2P_BOUNCE_COMBO):
        return ('E', 'REJECTED',
                'Circular fund flow detected with repeated bounce charges - '
                'funds cycling between same counterparties with payment failures')

    # GST turnover inflation
    if features.get('gst_to_bank_variance', 0) > T_GST_VARIANCE_REJECT:
        return ('E', 'REJECTED',
                'Declared GST turnover does not match actual bank credits - '
                'possible inflation of turnover to appear eligible for larger loan')

    # Excessive bounces
    if features.get('bounced_transaction_count', 0) >= T_BOUNCE_HARD_REJECT:
        return ('E', 'REJECTED',
                'Excessive payment failures - five or more bounce charges '
                'indicate chronic inability to meet obligations')

    # Balance inflation + new identity (balance stacking fraud)
    if (features.get('eod_balance_volatility', 0) > T_BALANCE_INFLATION_VOL and
        features.get('telecom_number_vintage_days', 0) < T_NEW_SIM_DAYS and
        features.get('utility_payment_consistency', 0) < 0.30):
        return ('E', 'REJECTED',
                'Balance inflation pattern detected - extreme balance volatility '
                'with new identity and minimal payment history indicates '
                'artificial balance stacking before loan application')

    # Identity mismatch + new SIM + bounces (combined fraud signal)
    if (features.get('identity_device_mismatch', 0) == 1 and
        features.get('telecom_number_vintage_days', 0) < T_NEW_SIM_DAYS and
        features.get('gst_filing_consistency_score', 0) == 0 and
        features.get('bounced_transaction_count', 0) >= 1):
        return ('E', 'REJECTED',
                'Multiple fraud indicators - identity mismatch combined with '
                'new SIM, no GST compliance, and payment failures')

    # Severe liquidity failure — BUT exempt seasonal farmers with good signals
    if features.get('min_balance_violation_count', 0) >= T_MIN_BAL_VIOLATION:
        is_seasonal = (features.get('revenue_seasonality_index', 0) > T_SEASONALITY_INDEX and
                       features.get('telecom_number_vintage_days', 0) > T_TELECOM_VINTAGE_STRONG and
                       features.get('bounced_transaction_count', 0) == 0)
        if is_seasonal:
            pass  # Don't reject — let it fall through to edge case or model
        else:
            return ('E', 'REJECTED',
                    'Account balance critically depleted three or more times - '
                    'severe and recurring liquidity failure')

    # Extreme cash dependency with bounces
    if (features.get('cash_withdrawal_dependency', 0) > T_CASH_DEPENDENCY_HIGH and
        features.get('bounced_transaction_count', 0) >= T_CASH_BOUNCE_COMBO):
        return ('E', 'REJECTED',
                'Extreme off-book cash dependency combined with payment failures - '
                'high probability of undisclosed financial obligations')

    # Unemployed applicant with any payment stress (demographic hard-reject)
    if (features.get('income_type_risk_score', 3) == T_CRITICAL_INCOME_RISK and
        features.get('bounced_transaction_count', 0) >= 1 and
        features.get('emergency_buffer_months', 0) < T_EMERGENCY_BUFFER_MIN):
        return ('E', 'REJECTED',
                'Unemployed applicant with payment failures and insufficient buffer - '
                'no declared income source and chronic payment stress indicates '
                'inability to service loan obligations')

    # ── TYPE 2: EDGE CASE PROTECTION ──

    # Clean established business with multi-signal trust
    if (features.get('bounced_transaction_count', 0) == 0 and
        features.get('p2p_circular_loop_flag', 0) == 0 and
        features.get('identity_device_mismatch', 0) == 0 and
        features.get('min_balance_violation_count', 0) == 0 and
        features.get('telecom_number_vintage_days', 0) > T_TELECOM_VINTAGE_STRONG and
        features.get('gst_filing_consistency_score', 0) >= T_GST_SCORE_STRONG and
        features.get('utility_payment_consistency', 0) >= T_UTILITY_CONSISTENCY and
        features.get('cash_withdrawal_dependency', 0) < T_CASH_DEPENDENCY_LOW):
        return ('A', 'APPROVED',
                'Established business with strong multi-signal trust - zero payment '
                'failures, long identity vintage, consistent GST filing, high utility '
                'discipline, and minimal cash dependency confirm exceptional creditworthiness')

    # Stable non-standard income (seasonal/agricultural)
    if (features.get('bounced_transaction_count', 0) == 0 and
        features.get('telecom_number_vintage_days', 0) > T_TELECOM_VINTAGE_STRONG and
        features.get('p2p_circular_loop_flag', 0) == 0 and
        features.get('gst_to_bank_variance', 0) < T_GST_VARIANCE_WARN and
        features.get('min_balance_violation_count', 0) == 0 and
        features.get('gst_filing_consistency_score', 0) > 0 and
        features.get('gst_to_bank_variance', 0) > 0):
        return ('B', 'APPROVED WITH CONDITIONS',
                'Stable non-standard income pattern - zero payment failures and '
                'long identity vintage confirm financial discipline despite irregular '
                'income timing consistent with seasonal or agricultural income')

    # NRI / platform / remittance income
    if (features.get('gst_filing_consistency_score', 0) == 0 and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('cash_withdrawal_dependency', 0) < T_CASH_DEPENDENCY_MEDIUM and
        features.get('telecom_number_vintage_days', 0) > T_TELECOM_VINTAGE_MEDIUM and
        features.get('p2p_circular_loop_flag', 0) == 0):
        return ('B', 'APPROVED WITH CONDITIONS',
                'Alternative income source verified - remittance or platform income '
                'with zero payment failures and fully digital spending confirms '
                'financial stability')

    # New business with strong identity signals
    if (features.get('business_vintage_months', 0) <= 12 and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('telecom_number_vintage_days', 0) > T_TELECOM_VINTAGE_NEW_BIZ and
        features.get('gst_filing_consistency_score', 0) <= T_GST_SCORE_NEW_BIZ and
        features.get('emergency_buffer_months', 0) > T_EMERGENCY_BUFFER_MIN):
        return ('B', 'APPROVED WITH CONDITIONS',
                'Stable pension or fixed income profile - consistent low-volatility '
                'credits with strong savings buffer and zero payment failures confirm '
                'reliable repayment capacity')

    # Stable senior / pensioner with clean profile
    # Must be in Type 2 so it fires before "first time borrower" Type 3 rule
    if (features.get('applicant_age_years', 35) >= T_AGE_SENIOR and
        features.get('income_type_risk_score', 3) == 2 and  # Pensioner
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('min_balance_violation_count', 0) == 0 and
        features.get('emergency_buffer_months', 0) > T_EMERGENCY_BUFFER_MIN):
        return ('B', 'APPROVED WITH CONDITIONS',
                'Stable pensioner profile - age 55+ with pension income, zero payment '
                'failures, and adequate liquidity buffer. Fixed pension income provides '
                'reliable repayment capacity. Recommend standard EMI on pension date')

    # ── TYPE 3: MANUAL REVIEW ──

    # P2P circular loop with ANY bounces (even below hard rejection threshold)
    if (features.get('p2p_circular_loop_flag', 0) == 1 and
        features.get('bounced_transaction_count', 0) >= 1):
        return ('C', 'MANUAL REVIEW',
                'Circular fund flow detected with payment bounce - circular '
                'transactions between same counterparties with at least one '
                'payment failure requires manual investigation')

    # P2P circular loop alone (no bounces but still suspicious)
    if features.get('p2p_circular_loop_flag', 0) == 1:
        return ('C', 'MANUAL REVIEW',
                'Circular fund flow detected - money cycling between same '
                'counterparties requires verification of genuine business purpose')

    # Zero-signal profile (new account with no history)
    signal_count = sum([
        features.get('utility_payment_consistency', 0) > 0,
        features.get('bounced_transaction_count', 0) > 0,
        features.get('telecom_number_vintage_days', 0) > 180,
        features.get('gst_filing_consistency_score', 0) > 0,
        features.get('emergency_buffer_months', 0) > 0.5,
        features.get('income_stability_score', 0) > 0.1,
        features.get('business_vintage_months', 0) > 6,
    ])
    if signal_count <= 1:
        return ('C', 'MANUAL REVIEW',
                'Insufficient credit signals - account has minimal financial '
                'history. Manual assessment required to verify identity and '
                'repayment capacity before loan disbursement')

    # Customer concentration with additional risk signals
    if (features.get('customer_concentration_ratio', 0) > T_CUSTOMER_CONCENTRATION and
        (features.get('telecom_number_vintage_days', 0) < T_TELECOM_VINTAGE_MEDIUM or
         features.get('gst_to_bank_variance', 0) > 0.3 or
         features.get('bounced_transaction_count', 0) > 0)):
        return ('C', 'MANUAL REVIEW',
                'Revenue concentrated in fewer than three customers with additional '
                'risk signals - single client dependency requires verification')

    # Turnover inflation
    if features.get('turnover_inflation_spike', 0) == 1:
        return ('C', 'MANUAL REVIEW',
                'Possible turnover inflation - round number transactions with GST '
                'variance requires verification')

    # Identity mismatch
    if features.get('identity_device_mismatch', 0) == 1:
        return ('C', 'MANUAL REVIEW',
                'Identity verification signals inconsistent - manual document check required')

    # Moderate bounce count with stress signals
    if (features.get('bounced_transaction_count', 0) >= T_BOUNCE_MODERATE and
        (features.get('cash_withdrawal_dependency', 0) > T_CASH_DEPENDENCY_MOD or
         features.get('eod_balance_volatility', 0) > T_EOD_VOLATILITY)):
        return ('C', 'MANUAL REVIEW',
                'Multiple payment bounces combined with cash dependency or balance '
                'volatility - moderate stress signals require manual assessment')

    # Sudden income drop with stress
    if (features.get('revenue_growth_trend', 0) < T_INCOME_DROP_SEVERE and
        features.get('emergency_buffer_months', 0) < T_INCOME_DROP_BUFFER and
        features.get('bounced_transaction_count', 0) >= T_INCOME_DROP_BOUNCES):
        return ('C', 'MANUAL REVIEW',
                'Significant income decline detected in recent months combined with '
                'reduced liquidity buffer and payment stress - verify cause of income '
                'drop before loan disbursement')

    # Geographic cluster risk
    if (features.get('region_risk_tier', 1) == T_REGION_HIGH_RISK and
        features.get('cashflow_volatility', 0) > T_CLUSTER_CASHFLOW and
        features.get('customer_concentration_ratio', 0) > T_CLUSTER_CONCENTRATION):
        return ('C', 'MANUAL REVIEW',
                'High geographic risk region combined with elevated cashflow volatility '
                'and customer concentration - verify business resilience to local '
                'economic conditions')

    # First time borrower with clean signals
    if (features.get('business_vintage_months', 0) <= T_NEW_BUSINESS_VINTAGE and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('min_balance_violation_count', 0) == 0 and
        features.get('gst_filing_consistency_score', 0) >= T_NEW_BIZ_GST_MIN and
        features.get('emergency_buffer_months', 0) > T_NEW_BIZ_BUFFER):
        return ('C', 'MANUAL REVIEW',
                'First time borrower with less than 6 months business history - '
                'behavioral signals are clean with zero payment failures and active '
                'GST compliance. Recommend manual assessment with focus on business '
                'plan and sector outlook')

    # Declining established business (was healthy, now failing)
    if (features.get('revenue_growth_trend', 0) < -0.40 and
        features.get('business_vintage_months', 0) > 24 and
        features.get('emergency_buffer_months', 0) < 2.0):
        return ('C', 'MANUAL REVIEW',
                'Established business showing significant revenue decline - '
                'business has operated for 2+ years but recent revenue trend is '
                'strongly negative with limited buffer. Verify cause of decline '
                'and recovery prospects before disbursement')

    # Consistently late payer with zero bounces (poor discipline, not fraud)
    if (features.get('avg_utility_dpd', 0) > 20 and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('utility_payment_consistency', 0) < 0.50):
        return ('C', 'MANUAL REVIEW',
                'Chronic late payment pattern detected - consistently pays utility '
                'bills 20+ days late but never bounces. Indicates poor financial '
                'discipline rather than inability to pay. Recommend structured '
                'repayment schedule with auto-debit mandate')

    # Seasonal farmer with min_bal violations but clean otherwise
    if (features.get('revenue_seasonality_index', 0) > T_SEASONALITY_INDEX and
        features.get('min_balance_violation_count', 0) >= T_MIN_BAL_VIOLATION and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('telecom_number_vintage_days', 0) > T_TELECOM_VINTAGE_STRONG):
        return ('C', 'MANUAL REVIEW',
                'Seasonal business with low-balance periods - balance drops below '
                'minimum during off-season months but maintains zero bounce record '
                'and long identity vintage. Recommend seasonal EMI structure aligned '
                'with harvest/revenue cycle')

    # Gig worker with some GST but irregular income
    if (features.get('income_seasonality_flag', 0) == 1 and
        features.get('income_stability_score', 0) < 0.40 and
        features.get('bounced_transaction_count', 0) == 0 and
        features.get('gst_filing_consistency_score', 0) > 0 and
        features.get('gst_filing_consistency_score', 0) < T_GST_SCORE_STRONG and
        features.get('cash_withdrawal_dependency', 0) < T_CASH_DEPENDENCY_MEDIUM):
        return ('C', 'MANUAL REVIEW',
                'Gig or freelance income pattern - irregular income timing with '
                'partial GST compliance and zero payment failures. Recommend '
                'approval with income averaging and flexible EMI dates')

    # ── DEMOGRAPHIC RISK RULES (profile-driven) ──────────────────────────────

    # Young applicant with no assets and high-risk income type
    # Any behavioral stress elevates risk significantly for this segment
    if (features.get('applicant_age_years', 35) < T_AGE_YOUNG and
        features.get('owns_property', 0) == 0 and
        features.get('income_type_risk_score', 3) >= T_HIGH_INCOME_RISK and
        features.get('bounced_transaction_count', 0) >= 1):
        return ('C', 'MANUAL REVIEW',
                'Young applicant with no property, high-risk income type, and '
                'payment stress - combination of age, asset, and income instability '
                'requires manual income verification before disbursement')

    # High family burden with unstable income (can\'t service EMI under stress)
    if (features.get('family_burden_ratio', 0) > T_FAMILY_BURDEN_HIGH and
        features.get('income_type_risk_score', 3) >= T_HIGH_INCOME_RISK and
        features.get('emergency_buffer_months', 0) < T_EMERGENCY_BUFFER_MIN):
        return ('C', 'MANUAL REVIEW',
                'High family obligation ratio with unstable income and limited buffer - '
                'significant dependent burden combined with non-salaried income and '
                'thin cash reserves requires household income assessment')

    # Poor contactability with financial stress (verification risk)
    if (features.get('contactability_score', 2) <= T_CONTACT_POOR and
        features.get('bounced_transaction_count', 0) >= 1 and
        features.get('eod_balance_volatility', 0) > T_EOD_VOLATILITY):
        return ('C', 'MANUAL REVIEW',
                'Low contactability with financial stress signals - applicant has '
                'limited reachable contact points combined with payment failures and '
                'volatile account balance. Identity and address verification required')

    return None


if __name__ == '__main__':
    # Test 1: Wash trader → REJECT
    test_1 = {
        'p2p_circular_loop_flag': 1, 'bounced_transaction_count': 3,
        'gst_to_bank_variance': 0.5, 'min_balance_violation_count': 0,
        'cash_withdrawal_dependency': 0.3, 'telecom_number_vintage_days': 95,
        'gst_filing_consistency_score': 2, 'customer_concentration_ratio': 0.5,
        'turnover_inflation_spike': 0, 'identity_device_mismatch': 0,
        'business_vintage_months': 8, 'emergency_buffer_months': 0.5,
        'revenue_seasonality_index': 0.1, 'revenue_growth_trend': 0.0,
        'cashflow_volatility': 0.8, 'region_risk_tier': 2,
        'utility_payment_consistency': 0.5, 'eod_balance_volatility': 0.9
    }
    assert apply_pre_layer(test_1) is not None and apply_pre_layer(test_1)[0] == 'E', "FAIL: Farouk should be E"
    print("[OK] Rule 1 fires - Farouk -> E")

    # Test 2: Seasonal farmer → APPROVED WITH CONDITIONS
    test_2 = {
        'p2p_circular_loop_flag': 0, 'bounced_transaction_count': 0,
        'telecom_number_vintage_days': 3200, 'gst_to_bank_variance': 0.1,
        'min_balance_violation_count': 0, 'gst_filing_consistency_score': 4,
        'cash_withdrawal_dependency': 0.05, 'business_vintage_months': 72,
        'emergency_buffer_months': 3.0, 'customer_concentration_ratio': 0.6,
        'turnover_inflation_spike': 0, 'identity_device_mismatch': 0,
        'revenue_seasonality_index': 0.3, 'revenue_growth_trend': 0.05,
        'cashflow_volatility': 0.4, 'region_risk_tier': 2,
        'utility_payment_consistency': 0.8, 'eod_balance_volatility': 0.3
    }
    assert apply_pre_layer(test_2) is not None and apply_pre_layer(test_2)[0] == 'B', "FAIL: Sukhwinder should be B"
    print("[OK] Rule 6 fires - Sukhwinder -> B")

    # Test 3: NRI → APPROVED WITH CONDITIONS
    test_3 = {
        'p2p_circular_loop_flag': 0, 'bounced_transaction_count': 0,
        'gst_filing_consistency_score': 0, 'cash_withdrawal_dependency': 0.05,
        'telecom_number_vintage_days': 1800, 'min_balance_violation_count': 0,
        'gst_to_bank_variance': 0.5, 'business_vintage_months': 0,
        'emergency_buffer_months': 5.0, 'customer_concentration_ratio': 0.7,
        'turnover_inflation_spike': 0, 'identity_device_mismatch': 0,
        'revenue_seasonality_index': 0.2, 'revenue_growth_trend': 0.0,
        'cashflow_volatility': 0.3, 'region_risk_tier': 2,
        'utility_payment_consistency': 0.7, 'eod_balance_volatility': 0.3
    }
    assert apply_pre_layer(test_3) is not None and apply_pre_layer(test_3)[0] == 'B', "FAIL: Arjun should be B"
    print("[OK] Rule 7 fires - Arjun -> B")

    # Test 4: Ambiguous → None (goes to ML)
    test_4 = {
        'p2p_circular_loop_flag': 0, 'bounced_transaction_count': 1,
        'gst_to_bank_variance': 0.2, 'min_balance_violation_count': 1,
        'cash_withdrawal_dependency': 0.3, 'telecom_number_vintage_days': 600,
        'gst_filing_consistency_score': 5, 'customer_concentration_ratio': 0.5,
        'turnover_inflation_spike': 0, 'identity_device_mismatch': 0,
        'business_vintage_months': 24, 'emergency_buffer_months': 1.5,
        'revenue_seasonality_index': 0.2, 'revenue_growth_trend': -0.1,
        'cashflow_volatility': 0.3, 'region_risk_tier': 2,
        'utility_payment_consistency': 0.7, 'eod_balance_volatility': 0.3
    }
    assert apply_pre_layer(test_4) is None, "FAIL: ambiguous should be None"
    print("[OK] No rule fires - ambiguous -> None (goes to model)")

    # Test 5: Seasonal spike → MANUAL REVIEW (not rejected)
    test_seasonal = {
        'revenue_seasonality_index': 0.75,
        'gst_filing_consistency_score': 5,
        'gst_to_bank_variance': 1.8,
        'bounced_transaction_count': 0,
        'p2p_circular_loop_flag': 0,
        'min_balance_violation_count': 0,
        'cash_withdrawal_dependency': 0.1,
        'telecom_number_vintage_days': 900,
        'identity_device_mismatch': 0,
        'customer_concentration_ratio': 0.4,
        'turnover_inflation_spike': 0,
        'business_vintage_months': 36,
        'emergency_buffer_months': 2.5,
        'revenue_growth_trend': 0.3,
        'cashflow_volatility': 0.4,
        'region_risk_tier': 2,
        'utility_payment_consistency': 0.7,
        'eod_balance_volatility': 0.4
    }
    result = apply_pre_layer(test_seasonal)
    assert result is not None and result[0] == 'C', \
        f"FAIL: Seasonal spike should be C, got {result}"
    print("[OK] Seasonal rule fires - Diwali textile MSME -> C MANUAL REVIEW")

    # Test 6: GST fraud still rejects (non-seasonal)
    test_gst_fraud = {
        'revenue_seasonality_index': 0.1,
        'gst_filing_consistency_score': 1,
        'gst_to_bank_variance': 2.0,
        'bounced_transaction_count': 0,
        'p2p_circular_loop_flag': 0,
        'min_balance_violation_count': 0,
        'cash_withdrawal_dependency': 0.3,
        'telecom_number_vintage_days': 200,
        'identity_device_mismatch': 0,
        'customer_concentration_ratio': 0.4,
        'turnover_inflation_spike': 0,
        'business_vintage_months': 24,
        'emergency_buffer_months': 1.0,
        'revenue_growth_trend': 0.0,
        'cashflow_volatility': 0.5,
        'region_risk_tier': 2,
        'utility_payment_consistency': 0.5,
        'eod_balance_volatility': 0.5
    }
    result = apply_pre_layer(test_gst_fraud)
    assert result is not None and result[0] == 'E', \
        f"FAIL: GST fraud should be E, got {result}"
    print("[OK] GST fraud still rejects -> E REJECTED")

    # Test 7: Clean business APPROVE (tests bug fix)
    test_clean = {
        'bounced_transaction_count': 0,
        'p2p_circular_loop_flag': 0,
        'identity_device_mismatch': 0,
        'min_balance_violation_count': 0,
        'telecom_number_vintage_days': 1200,
        'gst_filing_consistency_score': 7,
        'utility_payment_consistency': 0.92,
        'cash_withdrawal_dependency': 0.08,
        'gst_to_bank_variance': 0.2,
        'customer_concentration_ratio': 0.3,
        'turnover_inflation_spike': 0,
        'business_vintage_months': 48,
        'emergency_buffer_months': 4.0,
        'revenue_seasonality_index': 0.2,
        'revenue_growth_trend': 0.05,
        'cashflow_volatility': 0.2,
        'region_risk_tier': 2,
        'eod_balance_volatility': 0.2
    }
    result = apply_pre_layer(test_clean)
    assert result is not None and result[0] == 'A', \
        f"FAIL: Clean business should be A, got {result}"
    print("[OK] Clean business APPROVE fires -> A APPROVED")

    # Test 8: First time borrower → MANUAL REVIEW
    test_new = {
        'business_vintage_months': 4,
        'bounced_transaction_count': 0,
        'min_balance_violation_count': 0,
        'gst_filing_consistency_score': 3,
        'emergency_buffer_months': 1.8,
        'p2p_circular_loop_flag': 0,
        'identity_device_mismatch': 0,
        'gst_to_bank_variance': 0.3,
        'cash_withdrawal_dependency': 0.15,
        'telecom_number_vintage_days': 800,
        'customer_concentration_ratio': 0.5,
        'turnover_inflation_spike': 0,
        'revenue_seasonality_index': 0.2,
        'revenue_growth_trend': 0.1,
        'cashflow_volatility': 0.3,
        'region_risk_tier': 2,
        'utility_payment_consistency': 0.7,
        'eod_balance_volatility': 0.3
    }
    result = apply_pre_layer(test_new)
    assert result is not None and result[0] == 'C', \
        f"FAIL: New borrower should be C, got {result}"
    print("[OK] First time borrower -> C MANUAL REVIEW")
