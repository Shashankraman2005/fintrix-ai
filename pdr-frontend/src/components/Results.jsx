import React, { useRef, useEffect, useState } from 'react';
import './Results.css';
import XaiTransparencySection from './XaiTransparencySection';
import TransactionForensics, { FRAUD_FLAGS } from './TransactionForensics';
import { generateCreditDecisionPDF } from './PdfReportGenerator';
import { useTheme } from './ThemeContext';
import ChatPanel from './ChatPanel';

// ... (PROFILE_DETAILS unchanged)
const PROFILE_DETAILS = {
  'NTC_001': { name: 'Priya Venkataraman', city: 'Chennai', persona: 'Clean Salaried Professional' },
  'NTC_002': { name: 'Ramesh Gowda', city: 'Mysuru', persona: 'Cash-Dependent Informal Worker' },
  'NTC_003': { name: 'Deepak Malhotra', city: 'Delhi', persona: 'Synthetic Fraud — Balance Inflation' },
  'MSME_001': { name: 'Sukhwinder Singh', city: 'Ludhiana', persona: 'Seasonal Agri Business' },
  'MSME_002': { name: 'Mohammed Farouk', city: 'Delhi', persona: 'Wash Trader — Circular Transaction Fraud' },
};

// ── Feature card configs split by model type ─────────────────
const NTC_FEATURES = [
  {
    key: 'bounced_transaction_count', label: 'Bounce Charges',
    tooltip: 'Times payments failed due to insufficient funds'
  },
  {
    key: 'utility_payment_consistency', label: 'Utility Bills Paid',
    tooltip: 'Consecutive months of on-time utility payments'
  },
  {
    key: 'cash_withdrawal_dependency', label: 'Cash Withdrawal',
    tooltip: '% of total debits taken as cash — flags off-book activity'
  },
  {
    key: 'min_balance_violation_count', label: 'Min Balance Violations',
    tooltip: 'Times account balance dropped to zero or below minimum'
  },
  {
    key: 'telecom_number_vintage_days', label: 'SIM Vintage (days)',
    tooltip: 'How long the mobile number has been active — identity anchor'
  },
  {
    key: 'avg_utility_dpd', label: 'Avg Utility DPD',
    tooltip: 'Average days past due on utility bills'
  },
  {
    key: 'emergency_buffer_months', label: 'Emergency Buffer',
    tooltip: 'Months of essential expenses covered by current balance'
  },
  {
    key: 'eod_balance_volatility', label: 'Balance Volatility',
    tooltip: 'Coefficient of variation of daily closing balance'
  },
];

const MSME_FEATURES = [
  {
    key: 'operating_cashflow_ratio', label: 'Cashflow Ratio',
    tooltip: 'Income vs expenses — above 1.2 means healthy surplus'
  },
  {
    key: 'gst_filing_consistency_score', label: 'GST Filing Score',
    tooltip: 'Consecutive months of on-time GST returns filed'
  },
  {
    key: 'gst_to_bank_variance', label: 'GST–Bank Variance',
    tooltip: 'Gap between GST declared revenue and bank inflows — fraud signal'
  },
  {
    key: 'customer_concentration_ratio', label: 'Client Concentration',
    tooltip: '% revenue from top 3 clients — 1.0 means fully dependent on one'
  },
  {
    key: 'avg_invoice_payment_delay', label: 'Invoice Delay (days)',
    tooltip: 'Avg days between invoice raised and payment received'
  },
  {
    key: 'cashflow_volatility', label: 'Revenue Volatility',
    tooltip: 'Coefficient of variation of monthly cashflow (0–1 scale)'
  },
  {
    key: 'vendor_payment_discipline', label: 'Vendor Pay DPD',
    tooltip: 'Average days past due when paying own suppliers'
  },
  {
    key: 'turnover_inflation_spike', label: 'Turnover Spike',
    tooltip: 'Flags unnatural volume spike 30–60 days before loan application'
  },
];

// ── Feature status thresholds ─────────────────────────────────
const getFeatureStatus = (key, val) => {
  if (val === null || val === undefined) return null;
  const rules = {
    bounced_transaction_count: v => v === 0 ? 'strong' : v <= 2 ? 'watch' : 'risk',
    utility_payment_consistency: v => v >= 6 ? 'strong' : v >= 3 ? 'watch' : 'risk',
    cash_withdrawal_dependency: v => v < 0.2 ? 'strong' : v <= 0.5 ? 'watch' : 'risk',
    min_balance_violation_count: v => v === 0 ? 'strong' : v <= 2 ? 'watch' : 'risk',
    telecom_number_vintage_days: v => v > 1000 ? 'strong' : v >= 365 ? 'watch' : 'risk',
    avg_utility_dpd: v => v < 3 ? 'strong' : v <= 7 ? 'watch' : 'risk',
    emergency_buffer_months: v => v >= 2 ? 'strong' : v >= 0.5 ? 'watch' : 'risk',
    eod_balance_volatility: v => v < 0.3 ? 'strong' : v <= 0.6 ? 'watch' : 'risk',
    operating_cashflow_ratio: v => v > 1.4 ? 'strong' : v >= 1 ? 'watch' : 'risk',
    gst_filing_consistency_score: v => v >= 6 ? 'strong' : v >= 3 ? 'watch' : 'risk',
    gst_to_bank_variance: v => v < 0.1 ? 'strong' : v <= 0.3 ? 'watch' : 'risk',
    customer_concentration_ratio: v => v < 0.4 ? 'strong' : v <= 0.7 ? 'watch' : 'risk',
    avg_invoice_payment_delay: v => v < 20 ? 'strong' : v <= 45 ? 'watch' : 'risk',
    // cashflow_volatility is a 0–1 ratio in the JSON schema
    cashflow_volatility: v => v < 0.25 ? 'strong' : v <= 0.5 ? 'watch' : 'risk',
    vendor_payment_discipline: v => v < 10 ? 'strong' : v <= 25 ? 'watch' : 'risk',
    turnover_inflation_spike: v => v === 0 ? 'strong' : 'risk',
  };
  const fn = rules[key];
  if (!fn) return null;
  // Guard: if cashflow_volatility comes through as a large rupee value
  // (backend bug), clamp it to a ratio so the chip still shows something
  // meaningful rather than always "risk".
  let safeVal = val;
  if (key === 'cashflow_volatility' && val > 10) {
    // Already caught by formatVal but we still need a sensible status —
    // large raw std-dev means high volatility, so mark as risk.
    return { label: 'Risk', cls: 'chip-risk' };
  }
  const s = fn(safeVal);
  return {
    strong: { label: 'Strong', cls: 'chip-strong' },
    watch: { label: 'Watch', cls: 'chip-watch' },
    risk: { label: 'Risk', cls: 'chip-risk' },
  }[s];
};

const formatVal = (key, val) => {
  if (val === null || val === undefined) return '—';
  if (key === 'cash_withdrawal_dependency') return `${(val * 100).toFixed(0)}%`;
  if (key === 'gst_to_bank_variance') return val.toFixed(2);
  if (key === 'eod_balance_volatility') return val.toFixed(2);
  if (key === 'turnover_inflation_spike') return val === 1 ? 'YES ⚠' : 'No';
  // cashflow_volatility should be a 0–1 ratio. If the backend accidentally
  // sends a large rupee std-dev, show it as a ratio placeholder so the card
  // doesn't display a five-digit number.
  if (key === 'cashflow_volatility') {
    if (typeof val === 'number' && val > 10) return '—';
    return typeof val === 'number' ? val.toFixed(2) : val;
  }
  if (Number.isInteger(val)) return val;
  if (typeof val === 'number') return val.toFixed(2);
  return val;
};

// ── Outcome helpers ───────────────────────────────────────────
const OUTCOME_STYLES = {
  'APPROVED': { cls: 'out-approved', icon: '✅' },
  'APPROVED WITH CONDITIONS': { cls: 'out-cond', icon: '⚠️' },
  'MANUAL REVIEW': { cls: 'out-review', icon: '🔍' },
  'REJECTED': { cls: 'out-rejected', icon: '❌' },
};

// ── Radar axis configs ────────────────────────────────────────
const buildRadarScores = (features = {}, isNTC) => {
  const clamp = (v, lo, hi) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
  const inv = (v, lo, hi) => 100 - clamp(v, lo, hi);

  if (isNTC) {
    return {
      labels: ['Payment Discipline', 'Liquidity Health', 'Identity Stability', 'Income Stability', 'Spending Behavior', 'Compliance'],
      scores: [
        Math.round(
          clamp(features.utility_payment_consistency || 0, 0, 12) * 0.5 +
          inv(Math.min(features.bounced_transaction_count || 0, 5), 0, 5) * 0.5
        ),
        Math.round(
          clamp(features.emergency_buffer_months || 0, 0, 4) * 0.4 +
          inv(Math.min(features.min_balance_violation_count || 0, 6), 0, 6) * 0.4 +
          inv(features.cash_withdrawal_dependency || 0, 0, 1) * 0.2
        ),
        Math.round(clamp(features.telecom_number_vintage_days || 0, 0, 3000)),
        Math.round(
          inv(features.eod_balance_volatility || 0, 0, 1) * 0.6 +
          inv(features.avg_utility_dpd || 0, 0, 15) * 0.4
        ),
        Math.round(clamp(features.essential_vs_lifestyle_ratio || 0, 0, 4)),
        Math.round(
          (features.p2p_circular_loop_flag ? 0 : 60) +
          inv(features.gst_to_bank_variance || 0, 0, 1) * 0.4
        ),
      ],
    };
  } else {
    // For MSME radar, cashflow_volatility must be in 0–1 range.
    // Clamp large values so the radar doesn't break.
    const cvRatio = (features.cashflow_volatility || 0) > 10
      ? 1.0
      : (features.cashflow_volatility || 0);

    return {
      labels: ['Operational', 'Network Risk', 'Compliance', 'Liquidity', 'MSME Health', 'Forensic'],
      scores: [
        Math.round(
          clamp(features.operating_cashflow_ratio || 0, 0.4, 2.5) * 0.6 +
          inv(cvRatio, 0, 1) * 0.4
        ),
        Math.round(
          inv(features.customer_concentration_ratio || 0, 0, 1) * 0.6 +
          clamp(features.repeat_customer_revenue_pct || 0, 0, 1) * 0.4
        ),
        Math.round(
          clamp(features.gst_filing_consistency_score || 0, 0, 12) * 0.5 +
          inv(features.gst_to_bank_variance || 0, 0, 0.65) * 0.5
        ),
        Math.round(inv(features.avg_invoice_payment_delay || 0, 0, 120)),
        Math.round(
          clamp(features.business_vintage_months || 0, 0, 120) * 0.7 +
          clamp((features.revenue_growth_trend || 0) + 0.2, 0, 0.5) * 0.3
        ),
        Math.round(
          (features.turnover_inflation_spike ? 0 : 60) +
          inv(features.gst_to_bank_variance || 0, 0, 0.65) * 0.4
        ),
      ],
    };
  }
};

// ── What-If Credit Score Simulator Component ──────────────────
function WhatIfSimulator({ shapReasons, features, defaultProbability, isNTC, isDark }) {
  const topShap = React.useMemo(() => {
    if (!shapReasons || shapReasons.length === 0) return [];
    return [...shapReasons]
      .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
      .slice(0, 6);
  }, [shapReasons]);

  const featureConfigs = {
    operating_cashflow_ratio: { min: 0.2, max: 3.0, step: 0.05, unit: '', higherIsGood: true },
    avg_invoice_payment_delay: { min: 0, max: 120, step: 1, unit: ' days', higherIsGood: false },
    bounced_transaction_count: { min: 0, max: 10, step: 1, unit: ' times', higherIsGood: false },
    min_balance_violation_count: { min: 0, max: 10, step: 1, unit: ' times', higherIsGood: false },
    utility_payment_consistency: { min: 0, max: 12, step: 1, unit: ' mos', higherIsGood: true },
    gst_filing_consistency_score: { min: 0, max: 12, step: 1, unit: ' mos', higherIsGood: true },
    gst_to_bank_variance: { min: 0, max: 1.0, step: 0.02, unit: '', higherIsGood: false },
    cash_withdrawal_dependency: { min: 0, max: 1.0, step: 0.02, unit: '', higherIsGood: false },
    emergency_buffer_months: { min: 0, max: 6.0, step: 0.1, unit: ' mos', higherIsGood: true },
    telecom_number_vintage_days: { min: 30, max: 3000, step: 30, unit: ' days', higherIsGood: true },
    avg_utility_dpd: { min: 0, max: 30, step: 1, unit: ' days', higherIsGood: false },
    cashflow_volatility: { min: 0, max: 1.0, step: 0.02, unit: '', higherIsGood: false },
    customer_concentration_ratio: { min: 0, max: 1.0, step: 0.02, unit: '', higherIsGood: false },
  };

  const [sliderValues, setSliderValues] = useState({});

  useEffect(() => {
    const initial = {};
    topShap.forEach(item => {
      const k = item.feature;
      initial[k] = features[k] ?? 0;
    });
    setSliderValues(initial);
  }, [topShap, features]);

  if (!topShap || topShap.length === 0) return null;

  const basePD = defaultProbability ?? 0.20;
  const actualScore = Math.round(850 - basePD * 550);

  let totalDeltaPD = 0;
  topShap.forEach(item => {
    const k = item.feature;
    const actual = features[k] ?? 0;
    const current = sliderValues[k] !== undefined ? sliderValues[k] : actual;
    const config = featureConfigs[k] || { min: 0, max: Math.max(actual * 2, 10), step: 0.1, unit: '', higherIsGood: item.direction === 'strength' };
    
    const magnitude = Math.abs(item.shap_value) || 0.05;
    const span = (config.max - config.min) || 1;
    const deltaNormalized = (current - actual) / span;

    const directionFactor = config.higherIsGood ? -1 : 1;
    totalDeltaPD += deltaNormalized * magnitude * 0.4 * directionFactor;
  });

  const estimatedPD = Math.max(0.01, Math.min(0.99, basePD + totalDeltaPD));
  const estimatedScore = Math.round(850 - estimatedPD * 550);
  const scoreDiff = estimatedScore - actualScore;

  const getGrade = (pd) => {
    if (pd < 0.05) return { text: 'Grade A', cls: '#10B981' };
    if (pd < 0.15) return { text: 'Grade B', cls: '#3B82F6' };
    if (pd < 0.30) return { text: 'Grade C', cls: '#F59E0B' };
    if (pd < 0.50) return { text: 'Grade D', cls: '#F97316' };
    return { text: 'Grade E', cls: '#F43F5E' };
  };

  const estGrade = getGrade(estimatedPD);
  const actGrade = getGrade(basePD);

  const resetToActual = () => {
    const reset = {};
    topShap.forEach(item => {
      const k = item.feature;
      reset[k] = features[k] ?? 0;
    });
    setSliderValues(reset);
  };

  return (
    <div className="r-section" style={{ marginTop: 36 }}>
      <div style={{
        background: isDark ? 'linear-gradient(135deg, rgba(18, 21, 28, 0.95), rgba(30, 41, 59, 0.85))' : 'linear-gradient(135deg, #ffffff, #f8fafc)',
        borderRadius: 16,
        padding: '24px 28px',
        border: `1px solid ${isDark ? 'rgba(124, 58, 237, 0.3)' : 'rgba(99, 102, 241, 0.25)'}`,
        boxShadow: isDark ? '0 12px 32px rgba(0,0,0,0.5), 0 0 20px rgba(124, 58, 237, 0.15)' : '0 12px 32px rgba(99, 102, 241, 0.08)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 className="r-section-title" style={{ margin: 0 }}>"What-If" Credit Score Simulator</h2>
              <span style={{
                background: 'linear-gradient(135deg, #4338CA 0%, #7C3AED 100%)',
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: 99,
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
              }}>
                Interactive
              </span>
            </div>
            <p style={{ fontSize: 12, color: isDark ? '#94A3B8' : '#64748B', marginTop: 4 }}>
              Drag feature sliders to see real-time impact on estimated credit score based on applicant's SHAP weights.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: 6,
              background: isDark ? 'rgba(244, 63, 94, 0.15)' : '#FFE4E6',
              color: isDark ? '#F43F5E' : '#9F1239',
              border: `1px solid ${isDark ? 'rgba(244, 63, 94, 0.3)' : '#FECDD3'}`,
            }}>
              ⚠️ Estimated — not a live re-score
            </span>
            <button
              onClick={resetToActual}
              style={{
                fontSize: 12,
                fontWeight: 600,
                padding: '6px 14px',
                borderRadius: 8,
                background: isDark ? '#334155' : '#E2E8F0',
                color: isDark ? '#F8FAFC' : '#1E293B',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              🔄 Reset to actual
            </button>
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 16,
          padding: '18px 20px',
          borderRadius: 12,
          background: isDark ? 'rgba(15, 23, 42, 0.7)' : '#F1F5F9',
          marginBottom: 24,
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'}`,
        }}>
          <div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: isDark ? '#94A3B8' : '#64748B', fontWeight: 600 }}>Actual Score</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: isDark ? '#F8FAFC' : '#0F172A', fontFamily: 'monospace' }}>
              {actualScore} <span style={{ fontSize: 12, color: actGrade.cls, fontWeight: 700 }}>({actGrade.text})</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: isDark ? '#94A3B8' : '#64748B', fontWeight: 600 }}>Estimated Score</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#7C3AED', fontFamily: 'monospace' }}>
              {estimatedScore} <span style={{ fontSize: 12, color: estGrade.cls, fontWeight: 700 }}>({estGrade.text})</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: isDark ? '#94A3B8' : '#64748B', fontWeight: 600 }}>Simulated Shift</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: scoreDiff > 0 ? '#10B981' : scoreDiff < 0 ? '#F43F5E' : (isDark ? '#94A3B8' : '#64748B'), fontFamily: 'monospace' }}>
              {scoreDiff > 0 ? `+${scoreDiff}` : scoreDiff} pts
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: isDark ? '#94A3B8' : '#64748B', fontWeight: 600 }}>Estimated Default Prob.</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: estimatedPD < 0.2 ? '#10B981' : estimatedPD < 0.5 ? '#F59E0B' : '#F43F5E', fontFamily: 'monospace' }}>
              {(estimatedPD * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
          {topShap.map((item, idx) => {
            const k = item.feature;
            const actual = features[k] ?? 0;
            const config = featureConfigs[k] || { min: 0, max: Math.max(actual * 2, 10), step: 0.1, unit: '', higherIsGood: item.direction === 'strength' };
            const current = sliderValues[k] !== undefined ? sliderValues[k] : actual;
            const diff = current - actual;

            return (
              <div key={idx} style={{
                background: isDark ? 'rgba(30, 41, 59, 0.5)' : '#FFFFFF',
                borderRadius: 12,
                padding: '16px 18px',
                border: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : '#E2E8F0'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: isDark ? '#F1F5F9' : '#1E293B' }}>{item.reason}</div>
                    <div style={{ fontSize: 11, fontFamily: 'monospace', color: isDark ? '#94A3B8' : '#64748B' }}>{k}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: isDark ? '#F8FAFC' : '#0F172A', fontFamily: 'monospace' }}>
                      {typeof current === 'number' && !Number.isInteger(current) ? current.toFixed(2) : current}{config.unit}
                    </span>
                    {Math.abs(diff) > 0.001 && (
                      <div style={{ fontSize: 10, fontWeight: 700, color: (config.higherIsGood ? diff > 0 : diff < 0) ? '#10B981' : '#F43F5E' }}>
                        {diff > 0 ? '+' : ''}{typeof diff === 'number' && !Number.isInteger(diff) ? diff.toFixed(2) : diff}
                      </div>
                    )}
                  </div>
                </div>

                <input
                  type="range"
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  value={current}
                  onChange={(e) => setSliderValues(prev => ({ ...prev, [k]: parseFloat(e.target.value) }))}
                  style={{
                    width: '100%',
                    height: 6,
                    borderRadius: 3,
                    accentColor: '#7C3AED',
                    cursor: 'pointer',
                  }}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: isDark ? '#64748B' : '#94A3B8', marginTop: 4 }}>
                  <span>Min: {config.min}{config.unit}</span>
                  <span>Actual: {typeof actual === 'number' && !Number.isInteger(actual) ? actual.toFixed(2) : actual}{config.unit}</span>
                  <span>Max: {config.max}{config.unit}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────
export default function Results({ result, error, onBack, transactions, selectedUser }) {
  const [exporting, setExporting] = useState(false);
  const [showForensics, setShowForensics] = useState(false);
  const { theme } = useTheme();
  
  const isDark = theme === 'dark';
  const chartTextColor = isDark ? '#9ca3af' : '#6b7280';
  const chartGridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)';
  const profile = result?.profile || PROFILE_DETAILS[result?.user_id] || {};
  const isNTC = result?.user_id?.startsWith('NTC') || result?.model === 'NTC';
  const features = result?.features || {};
  const radar = result ? buildRadarScores(features, isNTC) : { labels: [], scores: [] };

  const outcomeStyle = OUTCOME_STYLES[result?.outcome] || OUTCOME_STYLES['MANUAL REVIEW'];
  const grade = (result?.grade || 'C').toUpperCase();

  const hasShap = result?.shap_reasons?.length > 0;
  const maxAbsShap = hasShap ? Math.max(...result.shap_reasons.map(s => Math.abs(s.shap_value))) : 1;
  const normalizedShaps = hasShap
    ? result.shap_reasons.map(s => ({ ...s, normalizedPct: (Math.abs(s.shap_value) / maxAbsShap) * 100 }))
    : [];

  // ── Verdict narrative ───────────────────────────────────────
  const buildVerdict = () => {
    const name = profile?.name?.split(' ')[0] || 'The applicant';

    // Grade A — clean approval
    if (grade === 'A') return {
      headline: 'Strong identity and zero payment failures',
      para: `${name} shows ${features.bounced_transaction_count ?? 0} bounce charges over 6 months with consistent utility payments and a SIM active for ${Math.round(features.telecom_number_vintage_days ?? 0).toLocaleString()} days — a strong identity anchor. No circular fund flows detected.`,
    };

    // Grade E — rejection. Use persona/model to pick the right story.
    if (grade === 'E' || result.outcome === 'REJECTED') {
      // MSME wash trader
      if (!isNTC || profile?.persona?.toLowerCase().includes('wash') || profile?.persona?.toLowerCase().includes('fraud')) {
        if (!isNTC) return {
          headline: 'Forensic flags override — Circular transaction pattern',
          para: `${name}'s GST declares ₹${((features.gst_declared_turnover || 5000000) / 100000).toFixed(0)}L turnover but bank inflows show only a fraction. Money cycles A→B→A monthly (circular loop detected). Turnover spike of 5x in the 45 days before application.`,
        };
      }
      // NTC fraud (Deepak)
      return {
        headline: 'Multiple fraud signals — Balance inflation detected',
        para: `${name}'s account balance spiked from near-zero to ₹10L+ in a single transfer, coinciding with a new SIM registered ${features.telecom_number_vintage_days ?? 0} days ago. Round-number P2P loops detected every month — a classic loan-stacking pattern.`,
      };
    }

    // Grade C — cash dependent informal worker (Ramesh)
    if (grade === 'C') return {
      headline: 'Consistent income but high cash dependency flags risk',
      para: `${name} deposits reliably each month but withdraws ${Math.round((features.cash_withdrawal_dependency ?? 0) * 100)}% of outflows as cash — masking true spending behavior. Balance hits zero ${features.min_balance_violation_count ?? 0} times in 6 months. Loan repayment capacity is uncertain.`,
    };

    // Grade B MSME seasonal agri (Sukhwinder)
    if (!isNTC && (grade === 'B' || profile?.persona?.toLowerCase().includes('seasonal'))) return {
      headline: 'Reliable history with seasonal income gaps',
      para: `${name} shows near-zero activity for 4 months, then receives ₹2.8L–₹3.1L from APMC mandi during harvest. A generic model would reject this as fragile. FintrixAi recognises the agricultural cycle — GST variance is low (${(features.gst_to_bank_variance ?? 0).toFixed(2)}) and business vintage is ${features.business_vintage_months ?? 0} months.`,
    };

    // Fallback
    return {
      headline: 'Moderate profile — conditions apply',
      para: `${name} shows a viable but mixed profile. Key watch areas have been flagged for review before final disbursement.`,
    };
  };

  const verdict = buildVerdict();

  // ── Chart refs ──────────────────────────────────────────────
  const timelineChartRef = useRef(null);
  const radarChartRef = useRef(null);

  useEffect(() => {
    if (!result) return;

    ['chartInstance'].forEach(k => {
      if (timelineChartRef.current?.[k]) { timelineChartRef.current[k].destroy(); }
      if (radarChartRef.current?.[k]) { radarChartRef.current[k].destroy(); }
    });

    // ── Timeline chart — real transaction data ────────────────
    if (timelineChartRef.current && transactions?.length) {
      const monthMap = {};
      transactions.forEach(tx => {
        const d = new Date(tx.date);
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!monthMap[key]) monthMap[key] = { income: 0, expense: 0 };
        if (tx.amount > 0) monthMap[key].income += tx.amount;
        else monthMap[key].expense += Math.abs(tx.amount);
      });

      const sortedKeys = Object.keys(monthMap).sort().slice(-6);
      const labels = sortedKeys.map(k => {
        const [y, m] = k.split('-');
        return new Date(y, m - 1).toLocaleString('default', { month: 'short' });
      });
      const incomeData = sortedKeys.map(k => monthMap[k].income);
      const expenseData = sortedKeys.map(k => monthMap[k].expense);

      const ctx = timelineChartRef.current.getContext('2d');
      timelineChartRef.current.chartInstance = new window.Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'Income', data: incomeData, backgroundColor: '#22c55e', borderRadius: 3 },
            { label: 'Expenses', data: expenseData, backgroundColor: '#ef4444', borderRadius: 3 },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { 
              position: 'top', 
              labels: { 
                boxWidth: 10, 
                font: { size: 11 },
                color: chartTextColor
              } 
            },
            tooltip: {
              mode: 'index', intersect: false,
              callbacks: { label: ctx => `₹${(ctx.raw / 1000).toFixed(1)}k` }
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: chartGridColor },
              ticks: { 
                font: { size: 10 }, 
                color: chartTextColor,
                callback: v => '₹' + (v / 1000).toFixed(0) + 'k' 
              }
            },
            x: { 
              grid: { display: false },
              ticks: { font: { size: 10 }, color: chartTextColor } 
            },
          },
        },
      });
    }

    // ── Radar chart ───────────────────────────────────────────
    if (radarChartRef.current) {
      const gradeColors = {
        A: { bg: isDark ? 'rgba(34,197,94,0.2)' : 'rgba(22,163,74,0.15)', bc: '#22c55e' },
        B: { bg: isDark ? 'rgba(59,130,246,0.2)' : 'rgba(37,99,235,0.15)', bc: '#3b82f6' },
        C: { bg: isDark ? 'rgba(234,179,8,0.2)' : 'rgba(202,138,4,0.15)', bc: '#eab308' },
        D: { bg: isDark ? 'rgba(249,115,22,0.2)' : 'rgba(234,88,12,0.15)', bc: '#f97316' },
        E: { bg: isDark ? 'rgba(239,68,68,0.2)' : 'rgba(220,38,38,0.15)', bc: '#ef4444' },
      };
      const { bg, bc } = gradeColors[grade] || gradeColors.C;

      const ctx = radarChartRef.current.getContext('2d');
      radarChartRef.current.chartInstance = new window.Chart(ctx, {
        type: 'radar',
        data: {
          labels: radar.labels,
          datasets: [{
            label: 'Score',
            data: radar.scores,
            backgroundColor: bg,
            borderColor: bc,
            borderWidth: 2,
            pointBackgroundColor: bc,
            pointRadius: 3,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => `${ctx.raw}/100` } },
          },
          scales: {
            r: {
              min: 0, max: 100,
              ticks: { display: false, stepSize: 25 },
              angleLines: { color: chartGridColor },
              grid: { color: chartGridColor },
              pointLabels: { 
                font: { size: 10 }, 
                color: chartTextColor 
              },
            },
          },
        },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, transactions, isDark, chartTextColor, chartGridColor]);

  // ── Render ──────────────────────────────────────────────────
  if (error) {
    return (
      <div className="results-container">
        <button className="r-back-btn" onClick={onBack}>← Back to profiles</button>
        <div className="error-banner">
          <h3>Error Occurred</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }
  if (!result) return null;

  const featureDefs = isNTC ? NTC_FEATURES : MSME_FEATURES;

  return (
    <>
      <div className="results-container">
        <button className="r-back-btn" onClick={onBack}>← Back to profiles</button>

        {/* Header */}
        <div className="r-header">
          <div className="r-header-left">
            <div className="r-label">CREDIT DECISION</div>
            <div className="r-name">{profile?.name || result.user_id}</div>
            <div className="r-persona">{profile?.persona || '—'} · {profile?.city || '—'}</div>
            <div className={`r-outcome ${outcomeStyle.cls}`}>
              {outcomeStyle.icon} {result.outcome}
            </div>
          </div>
          <div className="r-header-right">
            <div className={`r-grade r-grade-${grade.toLowerCase()}`}>{grade}</div>
            <div className="r-grade-label">Risk Grade</div>
            <div className={`r-model-tag ${isNTC ? 'tag-ntc' : 'tag-msme'}`}>
              {isNTC ? 'NTC Model' : 'MSME Model'}
            </div>
          </div>
        </div>

        <div className="r-divider" />

        {/* Source banner */}
        <div className={`r-source-banner ${result.decision_source === 'pre_layer' ? 'src-pre' : 'src-model'}`}>
          <div className="r-source-left">
            <span className="r-source-label">
              {result.decision_source === 'pre_layer' ? 'Rule-based Decision' : 'ML Model Decision'}
            </span>
            <span className="r-source-desc">
              {result.decision_source === 'pre_layer'
                ? 'Triggered by hard business rule — no model consultation required'
                : `Scored by ${isNTC ? 'NTC behavioral model' : 'MSME XGBoost model'} with SHAP explainability`}
            </span>
          </div>
          <div className="r-source-right">
            {result.default_probability != null
              ? `Default Probability: ${(result.default_probability * 100).toFixed(1)}%`
              : 'N/A — Rule override'}
          </div>
        </div>

        {/* Verdict card */}
        <div className="r-verdict-card">
          <div className="r-verdict-top">
            <div className="r-verdict-icon">{outcomeStyle.icon}</div>
            <div className="r-verdict-text">
              <h3 className="r-verdict-headline">{verdict.headline}</h3>
              <p className="r-verdict-para">{verdict.para}</p>
            </div>
          </div>

          {/* Active flags */}
          {result.active_flags?.length > 0 && (
            <div className="r-flags">
              {result.active_flags.map((flag, i) => (
                <span key={i} className="r-flag-chip">{flag.replace(/_/g, ' ')}</span>
              ))}
            </div>
          )}

          {/* Top SHAP drivers mini bar */}
          {hasShap && (
            <div className="r-verdict-mini-chart">
              <div className="mini-chart-label">Top Decision Drivers</div>
              {[...normalizedShaps]
                .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
                .slice(0, 3)
                .map((d, i) => (
                  <div className="mini-chart-row" key={i}>
                    <div className="mini-chart-name">{d.reason}</div>
                    <div className="mini-chart-bar-area">
                      <div
                        className={d.direction === 'strength' ? 'mini-bar-strength' : 'mini-bar-risk'}
                        style={{ width: `${d.normalizedPct}%`, ...(d.direction !== 'strength' ? { marginLeft: 'auto' } : {}) }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Charts */}
        <div className="r-section">
          <h2 className="r-section-title" style={{ marginBottom: 4 }}>Decision Intelligence</h2>
          <div className="r-chart-subtitle">Derived from behavioral signals across {radar.labels.length} pillars</div>
          <div className="r-charts-grid">
            <div className="r-chart-box">
              <div className="r-chart-title">Monthly Cashflow Pattern</div>
              <div style={{ height: 220, width: '100%' }}>
                <canvas ref={timelineChartRef} />
              </div>
            </div>
            <div className="r-chart-box" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div className="r-chart-title" style={{ alignSelf: 'flex-start' }}>FintrixAi Risk Radar</div>
              <div style={{ height: 280, width: '100%', maxWidth: 480 }}>
                <canvas ref={radarChartRef} />
              </div>
            </div>
          </div>
        </div>

        {/* SHAP breakdown */}
        {hasShap && (
          <div className="r-section">
            <h2 className="r-section-title">Behavioral Signal Breakdown</h2>
            <div className="shap-legend">
              <div className="legend-item"><div className="r-shap-dot dot-strength" /> Pushes toward approval</div>
              <div className="legend-item"><div className="r-shap-dot dot-risk" /> Pushes toward rejection</div>
            </div>
            <div className="r-shap-list">
              {normalizedShaps.map((shap, idx) => (
                <div className="r-shap-row" key={idx} style={{ animationDelay: `${idx * 70}ms` }}>
                  <div className={`r-shap-dot ${shap.direction === 'risk' ? 'dot-risk' : 'dot-strength'}`} />
                  <div className="r-shap-mid">
                    <div className="r-shap-reason">{shap.reason}</div>
                  </div>
                  <div className="r-shap-bar-wrapper">
                    {shap.direction === 'strength'
                      ? <div className="r-shap-bar bar-strength" style={{ width: `${shap.normalizedPct}%`, left: 0 }} />
                      : <div className="r-shap-bar bar-risk" style={{ width: `${shap.normalizedPct}%`, right: 0 }} />}
                  </div>
                  <div className={`r-shap-impact ${shap.impact?.toLowerCase().includes('very') ? 'shap-very-high' : shap.impact?.toLowerCase().includes('high') ? 'shap-high' : 'shap-medium'}`}>
                    {shap.impact}
                  </div>
                  <div className={`r-shap-value ${shap.direction === 'risk' ? 'val-risk' : 'val-strength'}`}>
                    {shap.direction === 'risk' && shap.shap_value > 0 ? '+' : ''}{shap.shap_value.toFixed(4)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What-If Credit Score Simulator */}
        <WhatIfSimulator
          shapReasons={result?.shap_reasons}
          features={features}
          defaultProbability={result?.default_probability}
          isNTC={isNTC}
          isDark={isDark}
        />

        {/* Feature grid — NTC vs MSME aware */}
        <div className="r-section">
          <h2 className="r-section-title">
            Key Feature Values
            <span className="r-section-badge">{isNTC ? 'NTC Behavioral Signals' : 'MSME Business Signals'}</span>
          </h2>
          <div className="r-feature-grid">
            {featureDefs.map((kf, idx) => {
              const val = features[kf.key];
              const status = getFeatureStatus(kf.key, val);
              return (
                <div className="r-feature-cell tooltip-container" key={idx}>
                  <div className="r-f-top">
                    <div className="r-f-label">{kf.label}</div>
                    {status && <div className={`r-f-chip ${status.cls}`}>{status.label}</div>}
                  </div>
                  <div className="r-f-value">{formatVal(kf.key, val)}</div>
                  <div className="tooltip-text">{kf.tooltip}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Transaction Forensics toggle button */}
        {transactions?.length > 0 && (
          <div style={{ margin: '8px 0 4px' }}>
            <button
              onClick={() => setShowForensics(v => !v)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 20px',
                borderRadius: 10,
                border: `1.5px solid ${isDark ? '#334155' : '#e2e8f0'}`,
                background: showForensics ? (isDark ? '#334155' : '#0f172a') : (isDark ? '#1e293b' : '#fff'),
                color: showForensics ? '#f1f5f9' : (isDark ? '#f8fafc' : '#0f172a'),
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.18s',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                {showForensics ? 'visibility_off' : 'manage_search'}
              </span>
              {showForensics ? 'Hide Transaction Forensics' : 'View Transaction Forensics'}
              {result.active_flags?.some(f => FRAUD_FLAGS.includes(f)) && (
                <span style={{
                  background: isDark ? 'rgba(153, 27, 27, 0.2)' : '#fef2f2',
                  color: isDark ? '#f87171' : '#991b1b',
                  border: `1px solid ${isDark ? '#7f1d1d' : '#fecaca'}`,
                  borderRadius: 20, padding: '1px 8px', fontSize: 10, fontWeight: 700,
                }}>
                  Signals detected
                </span>
              )}
            </button>
          </div>
        )}

        {showForensics && (
          <TransactionForensics transactions={transactions} isDark={isDark} />
        )}

        <XaiTransparencySection
          userProfile={{
            ...profile,
            features,
            isNTC,
            shap_reasons: result.shap_reasons,
            active_flags: result.active_flags
          }}
        />

        {/* ── Loan Offer / Alternative Path ──────────────────────────── */}
        {result.loan_offer && (
          result.loan_offer.eligible ? (
            /* APPROVED — show loan parameters */
            <div className="r-section">
              <h2 className="r-section-title">
                Indicative Loan Offer
                <span className="r-section-badge" style={isDark ? { background: 'rgba(22, 101, 52, 0.2)', color: '#4ade80' } : { background: '#dcfce7', color: '#166534' }}>Grade {grade}</span>
              </h2>
              <div style={{
                background: isDark ? 'linear-gradient(135deg, rgba(22, 101, 52, 0.1) 0%, rgba(22, 101, 52, 0.2) 100%)' : 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
                border: `1px solid ${isDark ? '#166534' : '#86efac'}`,
                borderRadius: 16,
                padding: '24px 28px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: 20,
              }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: isDark ? '#4ade80' : '#166534', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Interest Rate</div>
                  <div style={{ fontSize: 26, fontWeight: 800, color: isDark ? '#22c55e' : '#15803d' }}>{result.loan_offer.interest_rate_display}</div>
                  <div style={{ fontSize: 12, color: isDark ? '#22c55e' : '#4ade80', marginTop: 2 }}>Reducing balance</div>
                </div>
                {result.loan_offer.max_loan_amount && (
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: isDark ? '#4ade80' : '#166534', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Max Loan Amount</div>
                    <div style={{ fontSize: 26, fontWeight: 800, color: isDark ? '#22c55e' : '#15803d' }}>
                      ₹{result.loan_offer.max_loan_amount >= 100000
                        ? `${(result.loan_offer.max_loan_amount / 100000).toFixed(1)}L`
                        : `${(result.loan_offer.max_loan_amount / 1000).toFixed(0)}K`}
                    </div>
                    <div style={{ fontSize: 12, color: isDark ? '#22c55e' : '#4ade80', marginTop: 2 }}>Based on income × multiplier</div>
                  </div>
                )}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: isDark ? '#4ade80' : '#166534', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Tenure Options</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {result.loan_offer.tenure_options_months.map(t => (
                      <span key={t} style={{ background: isDark ? 'rgba(34, 197, 94, 0.2)' : '#bbf7d0', color: isDark ? '#4ade80' : '#166534', borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600 }}>{t}M</span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: isDark ? '#4ade80' : '#166534', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Product</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: isDark ? '#4ade80' : '#166534', lineHeight: 1.4 }}>{result.loan_offer.recommended_product}</div>
                </div>
              </div>
              <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 10 }}>
                * Rates are indicative and subject to final underwriting. FintrixAi provides alternative data intelligence — disbursement decisions rest with the lending institution.
              </p>
            </div>
          ) : (
            /* REJECTED — show alternative products */
            <div className="r-section">
              <h2 className="r-section-title">
                Declined → Alternative Path
                <span className="r-section-badge" style={isDark ? { background: 'rgba(146, 64, 14, 0.2)', color: '#fbbf24' } : { background: '#fef3c7', color: '#92400e' }}>Referral Options</span>
              </h2>
              <p style={{ fontSize: 14, color: '#64748b', marginBottom: 20, lineHeight: 1.6 }}>
                This applicant does not qualify for conventional lending. The following alternative financial products may be suitable based on the risk profile.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
                {result.loan_offer.alternative_products.map((prod, i) => (
                  <div key={i} style={{
                    background: isDark ? '#1e293b' : 'var(--surface-container-lowest, #fff)',
                    border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
                    borderRadius: 14,
                    padding: '20px 18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 22, color: '#f59e0b' }}>{prod.icon}</span>
                      <div style={{ fontSize: 13, fontWeight: 700, color: isDark ? '#f8fafc' : '#0f172a' }}>{prod.name}</div>
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 800, color: '#f59e0b' }}>{prod.rate}</div>
                    <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>
                      Up to ₹{prod.max_amount >= 100000
                        ? `${(prod.max_amount / 100000).toFixed(1)}L`
                        : `${(prod.max_amount / 1000).toFixed(0)}K`}
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>{prod.detail}</div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 14 }}>
                * Alternative products are indicative referrals. FintrixAi earns a referral fee from partner institutions. The applicant is free to choose any product.
              </p>
            </div>
          )
        )}

        {/* ── AI Credit Analyst Chat Panel ── */}
        <ChatPanel
          applicantId={(result?.user_id || '').toLowerCase()}
          applicantName={profile?.name || result?.user_id || 'Applicant'}
          decision={result?.outcome || ''}
          isDark={isDark}
        />

        <div style={{ height: 100 }} />
      </div>

      {/* Sticky footer */}
      <div className="r-footer">
        <div className="r-footer-left">FintrixAi · Alternative Credit Intelligence</div>
        <div className="r-footer-right">
          <button className="r-btn-outline" onClick={onBack}>← Score another profile</button>
          <button
            className="r-btn-solid"
            disabled={exporting}
            onClick={() => {
              setExporting(true);
              try {
                generateCreditDecisionPDF(selectedUser, result);
              } catch (e) {
                console.error('PDF export failed:', e);
                alert('PDF export failed. Check console for details.');
              } finally {
                setTimeout(() => setExporting(false), 1000);
              }
            }}
          >
            {exporting ? '⏳ Generating…' : '📄 Export Decision'}
          </button>
        </div>
      </div>
    </>
  );
}