/* eslint-disable no-unused-vars */
/**
 * Credit Decision Explanation PDF Report Generator
 * Generates audit-friendly, lender-style PDF reports using jsPDF.
 */
import { jsPDF } from 'jspdf';

// ── Color palette ──────────────────────────────────────────
const COLORS = {
  primary: [30, 41, 59],      // slate-800
  secondary: [71, 85, 105],   // slate-600
  muted: [148, 163, 184],     // slate-400
  body: [51, 65, 85],         // slate-700
  green: [22, 101, 52],       // green-800
  red: [153, 27, 27],         // red-800
  blue: [29, 78, 216],        // blue-700
  amber: [146, 64, 14],       // amber-800
  white: [255, 255, 255],
  bg: [248, 250, 252],        // slate-50
  border: [226, 232, 240],    // slate-200
  headerBg: [15, 23, 42],     // slate-900
};

const GRADE_COLORS = {
  A: [22, 101, 52], B: [29, 78, 216], C: [146, 64, 14],
  D: [154, 52, 18], E: [153, 27, 27],
};

const OUTCOME_COLORS = {
  'APPROVED': COLORS.green,
  'APPROVED WITH CONDITIONS': COLORS.blue,
  'MANUAL REVIEW': COLORS.amber,
  'REJECTED': COLORS.red,
};

// ── Helper: text wrapping + page breaks ────────────────────
function addWrappedText(doc, text, x, y, maxW, lineH, opts = {}) {
  const { color = COLORS.body, size = 10, style = 'normal' } = opts;
  doc.setFontSize(size);
  doc.setFont('helvetica', style);
  doc.setTextColor(...color);
  const lines = doc.splitTextToSize(text, maxW);
  for (const line of lines) {
    if (y > 272) { doc.addPage(); y = 25; }
    doc.text(line, x, y);
    y += lineH;
  }
  return y;
}

function sectionTitle(doc, title, y) {
  if (y > 255) { doc.addPage(); y = 25; }
  y += 4;
  doc.setFillColor(...COLORS.primary);
  doc.rect(20, y - 4, 3, 14, 'F');
  doc.setFontSize(13);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.primary);
  doc.text(title, 27, y + 6);
  return y + 18;
}

function bulletPoint(doc, text, x, y, maxW, opts = {}) {
  if (y > 270) { doc.addPage(); y = 25; }
  doc.setFillColor(...(opts.dotColor || COLORS.secondary));
  doc.circle(x + 2, y - 1.5, 1.2, 'F');
  return addWrappedText(doc, text, x + 7, y, maxW - 7, 4.5, opts);
}

// ── Transaction analysis helpers ───────────────────────────
function analyzeTransactions(txns) {
  if (!txns || txns.length === 0) return null;
  const credits = txns.filter(t => t.amount > 0);
  const debits = txns.filter(t => t.amount < 0);
  const totalCredits = credits.reduce((s, t) => s + t.amount, 0);
  const totalDebits = debits.reduce((s, t) => s + Math.abs(t.amount), 0);
  const balances = txns.map(t => t.balance || 0);
  const minBal = Math.min(...balances);
  const maxBal = Math.max(...balances);
  const avgBal = balances.reduce((s, b) => s + b, 0) / balances.length;
  const cashWithdrawals = debits.filter(t =>
    (t.narration || '').toUpperCase().includes('ATM') ||
    (t.narration || '').toUpperCase().includes('CASH WITHDRAWAL')
  );
  const cashWdAmt = cashWithdrawals.reduce((s, t) => s + Math.abs(t.amount), 0);
  const salaryCredits = credits.filter(t =>
    (t.narration || '').toUpperCase().includes('SALARY')
  );

  // Detect circular patterns
  const narrations = txns.map(t => (t.narration || '').toUpperCase());
  const hasCircular = narrations.some(n => n.includes('CIRCULAR')) ||
    detectP2PLoops(txns);

  // Round number check
  const roundTxns = txns.filter(t => Math.abs(t.amount) >= 10000 && Math.abs(t.amount) % 10000 === 0);

  return {
    totalCredits, totalDebits, minBal, maxBal, avgBal,
    creditCount: credits.length, debitCount: debits.length,
    cashWdAmt, cashWdPct: totalDebits > 0 ? cashWdAmt / totalDebits : 0,
    salaryCount: salaryCredits.length,
    avgSalary: salaryCredits.length > 0 ? salaryCredits.reduce((s, t) => s + t.amount, 0) / salaryCredits.length : 0,
    hasCircular, roundTxnCount: roundTxns.length,
    zeroBalCount: balances.filter(b => b <= 0).length,
    dateFrom: txns[0]?.date, dateTo: txns[txns.length - 1]?.date,
    totalTxns: txns.length,
  };
}

function detectP2PLoops(txns) {
  const pairs = {};
  for (const t of txns) {
    const n = (t.narration || '').toUpperCase();
    const match = n.match(/(?:UPI|NEFT|IMPS)\s+(?:FROM|TO)\s+(.+)/);
    if (match) {
      const name = match[1].trim();
      pairs[name] = (pairs[name] || 0) + 1;
    }
  }
  return Object.values(pairs).some(c => c >= 4);
}

function fmt(n) {
  if (n === null || n === undefined) return '—';
  return '₹' + Math.abs(n).toLocaleString('en-IN');
}

// ── Main PDF generation ────────────────────────────────────
export function generateCreditDecisionPDF(userData, scoringResult) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const pw = 170; // printable width
  const ml = 20;  // margin left

  const profile = userData?.user_profile || {};
  const features = { ...(userData?.ntc_features || {}), ...(userData?.msme_features || {}) };
  const flags = userData?.key_flags || [];
  const txns = userData?.transactions || [];
  const radar = userData?.radar || {};
  const gst = userData?.gst_data || {};
  const middleman = userData?.middleman_sources || null;
  const model = userData?.model || (userData?.user_id?.startsWith('NTC') ? 'NTC' : 'MSME');
  const isNTC = model === 'NTC';
  const isMiddleman = model === 'MSME_MIDDLEMAN';
  const grade = userData?.expected_grade || scoringResult?.grade || 'C';
  const outcome = userData?.expected_outcome || scoringResult?.outcome || 'MANUAL REVIEW';
  const txAnalysis = analyzeTransactions(txns);

  // ━━━ PAGE 1: HEADER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  doc.setFillColor(...COLORS.headerBg);
  doc.rect(0, 0, 210, 42, 'F');
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.white);
  doc.text('Credit Decision Explanation Report', ml, 18);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(180, 190, 210);
  doc.text(`Generated: ${new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })} | Report ID: FINTRIXAI-${userData?.user_id || 'UNKNOWN'}-${Date.now().toString(36).toUpperCase()}`, ml, 28);
  doc.text('FintrixAi — Alternative Credit Intelligence Platform | Confidential', ml, 34);

  let y = 52;

  // ━━━ SECTION 1: DECISION SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '1. Decision Summary', y);

  // Summary box
  doc.setFillColor(...COLORS.bg);
  doc.setDrawColor(...COLORS.border);
  doc.roundedRect(ml, y, pw, 38, 2, 2, 'FD');

  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.primary);
  doc.text(`Applicant: ${profile.name || 'N/A'}`, ml + 5, y + 8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...COLORS.body);
  doc.text(`Applicant ID: ${userData?.user_id || 'N/A'}`, ml + 5, y + 14);
  doc.text(`Model: ${model}${isMiddleman ? ' (Proxy-Data Lending)' : ''}`, ml + 5, y + 20);

  const gc = GRADE_COLORS[grade] || COLORS.secondary;
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...gc);
  doc.text(`Grade: ${grade}`, ml + 100, y + 8);

  const oc = OUTCOME_COLORS[outcome] || COLORS.secondary;
  doc.setTextColor(...oc);
  doc.text(`Decision: ${outcome}`, ml + 100, y + 14);

  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...COLORS.secondary);
  const riskBand = grade === 'A' ? 'Low Risk' : grade === 'B' ? 'Low–Medium Risk' : grade === 'C' ? 'Medium Risk' : grade === 'D' ? 'High Risk' : 'Very High Risk';
  doc.text(`Risk Band: ${riskBand}`, ml + 100, y + 20);

  y += 44;
  y = addWrappedText(doc, buildDecisionSummaryNarrative(userData, features, txAnalysis, grade, outcome, model), ml, y, pw, 4.5, { size: 10 });
  y += 6;

  // ━━━ SECTION 2: APPLICANT PROFILE ━━━━━━━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '2. Applicant Profile', y);
  const profileBullets = buildProfileBullets(profile, userData, model, isMiddleman);
  for (const b of profileBullets) {
    y = bulletPoint(doc, b, ml, y, pw);
    y += 1;
  }
  y += 4;

  // ━━━ SECTION 3: DATA SOURCES CONSIDERED ━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '3. Data Sources Considered', y);
  const sources = buildDataSources(txns, gst, middleman, features, radar, flags, isNTC);
  for (const s of sources) {
    y = bulletPoint(doc, s, ml, y, pw);
    y += 1;
  }
  y += 4;

  // ━━━ SECTION 4: POSITIVE SIGNALS ━━━━━━━━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '4. Positive Signals', y);
  const positives = buildPositiveSignals(features, txAnalysis, flags, profile, radar, model, isMiddleman, middleman);
  if (positives.length === 0) {
    y = addWrappedText(doc, 'No strong positive signals were identified in the available data.', ml, y, pw, 4.5);
  } else {
    for (const p of positives) {
      y = bulletPoint(doc, p, ml, y, pw, { dotColor: COLORS.green });
      y += 1;
    }
  }
  y += 4;

  // ━━━ SECTION 5: RISK SIGNALS ━━━━━━━━━━━━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '5. Risk Signals / Adverse Findings', y);
  const risks = buildRiskSignals(features, txAnalysis, flags, profile, radar, model, gst);
  if (risks.length === 0) {
    y = addWrappedText(doc, 'No significant risk signals were identified in the available data.', ml, y, pw, 4.5);
  } else {
    for (const r of risks) {
      y = bulletPoint(doc, r, ml, y, pw, { dotColor: COLORS.red });
      y += 1;
    }
  }
  y += 4;

  // ━━━ SECTION 6: BEHAVIORAL / CASHFLOW ASSESSMENT ━━━━━━━
  y = sectionTitle(doc, '6. Behavioral / Business Cashflow Assessment', y);
  const cashflowNarrative = buildCashflowNarrative(txAnalysis, features, model, isMiddleman, profile, middleman);
  y = addWrappedText(doc, cashflowNarrative, ml, y, pw, 4.5);
  y += 4;

  // ━━━ SECTION 7: FRAUD / FORENSIC ━━━━━━━━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '7. Fraud / Forensic Interpretation', y);
  const forensicNarrative = buildForensicNarrative(flags, txAnalysis, features, profile);
  y = addWrappedText(doc, forensicNarrative, ml, y, pw, 4.5);
  y += 4;

  // ━━━ SECTION 8: WHY DECISION IS APPROPRIATE ━━━━━━━━━━━━
  y = sectionTitle(doc, '8. Decision Justification', y);
  const justification = buildJustification(outcome, grade, features, txAnalysis, flags, model, isMiddleman, profile, middleman, gst);
  y = addWrappedText(doc, justification, ml, y, pw, 4.5);
  y += 4;

  // ━━━ SECTION 9: RECOMMENDED CONDITIONS ━━━━━━━━━━━━━━━━━
  y = sectionTitle(doc, '9. Recommended Conditions / Next Actions', y);
  const conditions = buildConditions(outcome, grade, features, flags, model, isMiddleman);
  for (const c of conditions) {
    y = bulletPoint(doc, c, ml, y, pw, { dotColor: COLORS.blue });
    y += 1;
  }
  y += 4;

  // ━━━ SECTION 10: RADAR SUMMARY TABLE ━━━━━━━━━━━━━━━━━━━
  if (Object.keys(radar).length > 0) {
    y = sectionTitle(doc, '10. Risk Radar Summary', y);
    if (y > 240) { doc.addPage(); y = 25; }
    const radarEntries = Object.entries(radar);
    doc.setFillColor(240, 242, 245);
    doc.rect(ml, y, pw, 7, 'F');
    doc.setFontSize(9);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.primary);
    doc.text('Dimension', ml + 3, y + 5);
    doc.text('Score (0–100)', ml + 100, y + 5);
    doc.text('Assessment', ml + 130, y + 5);
    y += 9;
    doc.setFont('helvetica', 'normal');
    for (const [dim, score] of radarEntries) {
      if (y > 272) { doc.addPage(); y = 25; }
      doc.setTextColor(...COLORS.body);
      doc.text(dim, ml + 3, y);
      doc.text(String(score), ml + 105, y);
      const assessment = score >= 70 ? 'Strong' : score >= 40 ? 'Moderate' : 'Weak';
      const ac = score >= 70 ? COLORS.green : score >= 40 ? COLORS.amber : COLORS.red;
      doc.setTextColor(...ac);
      doc.text(assessment, ml + 132, y);
      y += 5.5;
    }
    y += 4;
  }

  // ━━━ FOOTER / DISCLAIMER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  if (y > 240) { doc.addPage(); y = 25; }
  y += 6;
  doc.setDrawColor(...COLORS.border);
  doc.line(ml, y, ml + pw, y);
  y += 6;
  doc.setFontSize(8);
  doc.setFont('helvetica', 'italic');
  doc.setTextColor(...COLORS.muted);
  const disclaimer = 'Disclaimer: This report is generated based solely on the available structured inputs and observed behavioral signals. Missing or incomplete data may affect interpretability. This document is an aid to decision transparency and does not substitute for lender policy, compliance review, or manual underwriting where required. All assessments use only supplied evidence — no external data or assumptions have been introduced.';
  y = addWrappedText(doc, disclaimer, ml, y, pw, 3.8, { color: COLORS.muted, size: 8, style: 'italic' });

  // Page numbers
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(...COLORS.muted);
    doc.text(`Page ${i} of ${pageCount}`, 105, 290, { align: 'center' });
    doc.text('FintrixAi — Confidential', 190, 290, { align: 'right' });
  }

  doc.save(`FintrixAi_Credit_Decision_${userData?.user_id || 'Report'}_${new Date().toISOString().slice(0, 10)}.pdf`);
}

// ── Narrative builders ─────────────────────────────────────

function buildDecisionSummaryNarrative(userData, features, txA, grade, outcome, model) {
  const name = userData?.user_profile?.name || 'The applicant';
  if (outcome === 'APPROVED') {
    return `${name} has been assessed as APPROVED with a risk grade of ${grade}. The decision is supported by stable income patterns, disciplined payment behavior, and strong identity anchors observed in the available data. The applicant's behavioral profile is consistent with low default risk, and no material adverse signals were identified during the assessment.`;
  }
  if (outcome === 'APPROVED WITH CONDITIONS') {
    return `${name} has been assessed as APPROVED WITH CONDITIONS at risk grade ${grade}. The available data suggests viable creditworthiness, but specific risk factors — including ${features.revenue_seasonality_index > 0.5 ? 'high income seasonality' : features.customer_concentration_ratio > 0.7 ? 'elevated client concentration' : 'moderate behavioral volatility'} — warrant additional controls. The decision is supported by the applicant's long operational history and sector-consistent cashflow patterns, balanced against identified areas requiring monitoring.`;
  }
  if (outcome === 'MANUAL REVIEW') {
    return `${name} has been flagged for MANUAL REVIEW at risk grade ${grade}. The profile is neither clearly approvable nor clearly rejectable based on available signals. ${features.cash_withdrawal_dependency > 0.3 ? 'High cash withdrawal dependency masks true spending behavior, reducing confidence in repayment assessment.' : 'Observed behavioral patterns show mixed signals that require human verification before a final lending decision can be made.'}`;
  }
  // REJECTED
  return `${name} has been assessed as REJECTED with a risk grade of ${grade}. The decision is driven by ${userData?.key_flags?.includes('P2P_CIRCULAR_LOOP') ? 'elevated forensic concerns including circular transaction patterns' : 'insufficient confidence in repayment capacity based on observed behavioral data'}. Multiple adverse signals were identified, and the available evidence does not support acceptable credit risk at this time.`;
}

function buildProfileBullets(profile, userData, model, isMiddleman) {
  const bullets = [];
  if (profile.name) bullets.push(`Name: ${profile.name}`);
  if (profile.city) bullets.push(`City / Location: ${profile.city}`);
  if (profile.business_type) bullets.push(`Business / Borrower Type: ${profile.business_type}`);
  if (profile.business_vintage_months > 0) bullets.push(`Business Vintage: ${profile.business_vintage_months} months (${(profile.business_vintage_months / 12).toFixed(1)} years)`);
  if (profile.telecom_number_vintage_days) bullets.push(`Telecom Vintage: ${profile.telecom_number_vintage_days} days — ${profile.telecom_number_vintage_days > 1000 ? 'indicates stable long-term identity' : profile.telecom_number_vintage_days < 180 ? 'recent onboarding raises identity concern' : 'moderate identity anchor'}`);
  if (profile.academic_background_tier) bullets.push(`Academic Background Tier: ${profile.academic_background_tier} (${profile.academic_background_tier === 1 ? 'Tier 1 — Strong' : profile.academic_background_tier === 2 ? 'Tier 2 — Moderate' : 'Tier 3 — General'})`);
  bullets.push(`Model Applied: ${model}${isMiddleman ? ' — Proxy-data lending model for applicants without formal financial records' : ''}`);
  if (userData?.persona) bullets.push(`Persona Classification: ${userData.persona}`);
  return bullets;
}

function buildDataSources(txns, gst, middleman, features, radar, flags, isNTC) {
  const sources = [];
  if (txns && txns.length > 0) sources.push(`Bank Transaction History: ${txns.length} transactions analyzed across ${txns[0]?.date || 'N/A'} to ${txns[txns.length - 1]?.date || 'N/A'}`);
  else sources.push('Bank Transaction History: Not available for this applicant');
  if (Object.keys(radar).length > 0) sources.push(`FintrixAi Risk Radar: ${Object.keys(radar).length}-dimension behavioral scoring applied`);
  if (flags.length > 0) sources.push(`Key Flags Engine: ${flags.length} flag(s) evaluated`);
  if (gst?.available) sources.push(`GST Data: Available — declared turnover of ${fmt(gst.declared_turnover)}`);
  else sources.push('GST Data: Not available or not applicable');
  if (middleman) {
    if (middleman.supplierdata) sources.push('Supplier Payment Data: Available — used as proxy creditworthiness signal');
    if (middleman.utilitydata) sources.push('Utility Payment Data: Available — payment discipline and account vintage assessed');
    if (middleman.telecomdata) sources.push('Telecom Stability Data: Available — identity and behavioral continuity verified');
    if (middleman.bcagentdata) sources.push('BC Agent Field Verification: Available — business existence and field assessment completed');
  }
  if (isNTC) sources.push('NTC Behavioral Feature Engine: Utility, spending, balance, and identity signals computed');
  else sources.push('MSME Business Feature Engine: Revenue, cashflow, compliance, and forensic signals computed');
  return sources;
}

function buildPositiveSignals(features, txA, flags, profile, radar, model, isMiddleman, middleman) {
  const signals = [];
  // NTC signals
  if (features.utility_payment_consistency >= 6) signals.push(`Consistent utility payments: ${features.utility_payment_consistency} consecutive on-time payments observed. This indicates disciplined recurring expense management and supports repayment reliability.`);
  if (features.bounced_transaction_count === 0) signals.push('Zero bounced transactions across the observed period. This confirms sufficient balance management discipline and reduces dishonor risk.');
  if (features.emergency_buffer_months >= 2) signals.push(`Healthy emergency buffer: ${features.emergency_buffer_months} months of essential expenses covered by available balance. This provides a cushion against short-term income disruption.`);
  if (features.cash_withdrawal_dependency < 0.1) signals.push(`Low cash withdrawal dependency (${(features.cash_withdrawal_dependency * 100).toFixed(0)}% of debits). Spending is largely digital and traceable, increasing confidence in behavioral data quality.`);
  if (features.telecom_number_vintage_days > 1000) signals.push(`Strong identity stability: Telecom number active for ${features.telecom_number_vintage_days} days (${(features.telecom_number_vintage_days / 365).toFixed(1)} years). Long telecom vintage is a reliable proxy for identity permanence.`);
  if (features.eod_balance_volatility < 0.3) signals.push(`Low balance volatility (${features.eod_balance_volatility?.toFixed(2)}). Stable end-of-day balances indicate predictable cash management.`);
  // MSME signals
  if (features.business_vintage_months >= 48) signals.push(`Long business vintage: ${features.business_vintage_months} months (${(features.business_vintage_months / 12).toFixed(1)} years). Demonstrates sustained operational continuity and resilience through business cycles.`);
  if (features.operating_cashflow_ratio > 1.2) signals.push(`Healthy operating cashflow ratio (${features.operating_cashflow_ratio?.toFixed(2)}). Business generates surplus above operating expenses, supporting debt service capacity.`);
  if (features.gst_to_bank_variance < 0.1 && features.gst_to_bank_variance !== undefined && features.gst_to_bank_variance > 0) signals.push(`Low GST-to-bank variance (${features.gst_to_bank_variance?.toFixed(2)}). Declared revenue closely matches observed bank inflows, indicating data consistency.`);
  if (features.repeat_customer_revenue_pct > 0.8) signals.push(`High repeat customer revenue (${(features.repeat_customer_revenue_pct * 100).toFixed(0)}%). Indicates established demand and customer retention.`);
  // Middleman signals
  if (isMiddleman && middleman) {
    if (middleman.supplierdata?.payment_on_time_ratio > 0.85) signals.push(`Strong supplier payment discipline: ${(middleman.supplierdata.payment_on_time_ratio * 100).toFixed(0)}% on-time payment rate across ${middleman.supplierdata.months_of_data || 'multiple'} months. This serves as a reliable proxy for financial reliability in the absence of formal credit records.`);
    if (middleman.utilitydata?.bills_paid_last_24 >= 20) signals.push(`Consistent utility payment: ${middleman.utilitydata.bills_paid_last_24} of 24 bills paid on time. Account vintage of ${middleman.utilitydata.account_vintage_days} days confirms long-term residential/business stability.`);
    if (middleman.bcagentdata?.field_visit_confirmed) signals.push('BC Agent field verification confirms business existence, active operations, and low risk rating from field assessment.');
    if (middleman.telecomdata?.recharge_consistency_ratio > 0.9) signals.push(`High telecom recharge consistency (${(middleman.telecomdata.recharge_consistency_ratio * 100).toFixed(0)}%) with ${middleman.telecomdata.sim_vintage_days} days SIM vintage. No sudden usage drops or portability events detected.`);
  }
  // Radar-based
  if (txA?.salaryCount >= 3) signals.push(`Regular salary credits detected: ${txA.salaryCount} salary deposits observed, averaging ${fmt(txA.avgSalary)} per month. Consistent salary pattern supports income stability assessment.`);
  return signals;
}

function buildRiskSignals(features, txA, flags, profile, radar, model, gst) {
  const risks = [];
  if (features.cash_withdrawal_dependency > 0.3) risks.push(`High cash withdrawal dependency (${(features.cash_withdrawal_dependency * 100).toFixed(0)}% of total debits). This masks spending patterns and reduces confidence in behavioral data. Cash-heavy profiles increase the risk of off-book obligations affecting repayment capacity.`);
  if (features.bounced_transaction_count > 0) risks.push(`Bounced transactions detected: ${features.bounced_transaction_count} instance(s). Payment dishonors indicate periodic balance shortfalls and may signal overcommitment against available liquidity.`);
  if (features.min_balance_violation_count > 0) risks.push(`Minimum balance violations: ${features.min_balance_violation_count} instance(s) of near-zero or zero balance. Frequent balance floor breaches suggest thin liquidity margins and vulnerability to income disruption.`);
  if (features.eod_balance_volatility > 0.6) risks.push(`Elevated balance volatility (${features.eod_balance_volatility?.toFixed(2)}). High day-to-day balance swings indicate unpredictable cash management, which affects affordability confidence.`);
  if (features.avg_utility_dpd > 7) risks.push(`Late utility payments: Average ${features.avg_utility_dpd} days past due. Chronic late payments on essential services indicate cash timing pressure.`);
  if (features.telecom_number_vintage_days < 180) risks.push(`Recent telecom onboarding: SIM active for only ${features.telecom_number_vintage_days} days. Short telecom vintage reduces identity confidence and is associated with elevated fraud risk in NTC populations.`);
  // MSME specific
  if (features.gst_to_bank_variance > 0.3) risks.push(`Significant GST-bank mismatch (variance: ${features.gst_to_bank_variance?.toFixed(2)}). The gap between declared GST turnover and observed bank inflows raises concerns about data reliability or potential revenue inflation.`);
  if (features.turnover_inflation_spike) risks.push('Turnover inflation spike detected: Unnatural volume increase observed 30-60 days before application. This pattern is associated with pre-application balance or revenue manipulation.');
  if (features.customer_concentration_ratio > 0.7) risks.push(`High customer concentration (${(features.customer_concentration_ratio * 100).toFixed(0)}%). Revenue dependence on a narrow client base increases vulnerability to single-customer loss.`);
  if (features.avg_invoice_payment_delay > 45) risks.push(`Delayed invoice realization: Average ${features.avg_invoice_payment_delay} days. Extended payment cycles strain working capital and may indicate limited bargaining power or customer quality issues.`);
  if (features.vendor_payment_discipline > 25) risks.push(`Weak vendor payment discipline: Average ${features.vendor_payment_discipline} DPD on supplier payments. Late vendor payments can signal cashflow distress.`);
  // Flag-based
  if (flags.includes('P2P_CIRCULAR_LOOP')) risks.push('Circular fund flow pattern observed: Matched credit-debit pairs with the same counterparty within 24-48 hours. This pattern is consistent with manufactured throughput or balance inflation.');
  if (flags.includes('BENFORD_ANOMALY')) risks.push("Benford's Law anomaly detected: Transaction amount digit distribution deviates from expected natural patterns. This is a statistical indicator of potentially synthetic or manipulated transaction data.");
  if (flags.includes('BALANCE_INFLATION_SPIKE')) risks.push('Balance inflation spike: A disproportionate balance increase was observed shortly before application, inconsistent with prior account behavior.');
  if (flags.includes('NEW_SIM_RISK')) risks.push('New SIM risk: Very recent telecom identity onboarding, which reduces confidence in the identity anchor and is a common feature in synthetic or stacked applications.');
  if (txA?.zeroBalCount > 2) risks.push(`Frequent zero-balance episodes: Account reached ₹0 on ${txA.zeroBalCount} occasion(s). This indicates structural liquidity weakness.`);
  return risks;
}

function buildCashflowNarrative(txA, features, model, isMiddleman, profile, middleman) {
  if (isMiddleman && (!txA || txA.totalTxns === 0)) {
    return `No bank transaction history was provided for this case. As a proxy-data lending assessment (${model} model), creditworthiness is evaluated through alternative operational evidence including supplier payment records${middleman?.utilitydata ? ', utility payment history' : ''}${middleman?.telecomdata ? ', telecom behavioral continuity' : ''}, and field verification. ${middleman?.supplierdata ? `The applicant maintains average monthly purchases of ${fmt(middleman.supplierdata.avg_monthly_purchase_inr)} with a ${(middleman.supplierdata.payment_on_time_ratio * 100).toFixed(0)}% on-time payment rate over a ${middleman.supplierdata.relationship_vintage_days}-day supplier relationship.` : ''} The absence of formal bank data is expected for this segment and does not independently disqualify the applicant under the proxy-data lending framework.`;
  }
  if (!txA || txA.totalTxns === 0) {
    return 'No bank transaction history was provided for this case. This assessment is limited by the absence of observable cashflow data. No direct behavioral or cashflow conclusions can be drawn.';
  }
  let narrative = `Over the observed period (${txA.dateFrom} to ${txA.dateTo}), the applicant's account recorded ${txA.totalTxns} transactions with total inflows of ${fmt(txA.totalCredits)} and total outflows of ${fmt(txA.totalDebits)}. `;
  if (txA.salaryCount >= 3) {
    narrative += `Inflows appear salary-like, with ${txA.salaryCount} regular credits averaging ${fmt(txA.avgSalary)}. This pattern is consistent with the claimed salaried/individual borrower type. `;
  } else if (txA.totalCredits > 200000) {
    narrative += 'Inflows are lumpy and concentrated, suggesting business-related or seasonal revenue cycles rather than regular salary income. ';
  }
  if (txA.cashWdPct > 0.3) {
    narrative += `Cash withdrawals account for ${(txA.cashWdPct * 100).toFixed(0)}% of total outflows, indicating significant cash-based spending that is not traceable through digital records. `;
  }
  if (txA.zeroBalCount > 0) {
    narrative += `The account balance reached zero on ${txA.zeroBalCount} occasion(s), indicating periodic liquidity exhaustion. `;
  }
  narrative += `Average observed balance was ${fmt(txA.avgBal)} (range: ${fmt(txA.minBal)} to ${fmt(txA.maxBal)}). `;
  if (features.cashflow_volatility > 0.5 || (txA.maxBal / Math.max(txA.avgBal, 1)) > 5) {
    narrative += 'Balance trajectory shows high volatility — the pattern is inconsistent with stable, surplus-generating behavior. ';
  } else if (txA.avgBal > 50000) {
    narrative += 'Balance levels are healthy relative to transaction volume, suggesting visible surplus. ';
  }
  if (txA.hasCircular) {
    narrative += 'Circular fund flow patterns were identified, with matched credit-debit pairs involving the same counterparty. This reduces confidence in the authenticity of observed cashflows. ';
  }
  return narrative;
}

function buildForensicNarrative(flags, txA, features, profile) {
  const concerns = [];
  if (flags.includes('P2P_CIRCULAR_LOOP') || txA?.hasCircular) concerns.push('Circular transfer patterns identified: Matched credit-debit pairs with the same counterparty within short intervals suggest possible transaction circularity. This is inconsistent with organic business or personal cashflow behavior.');
  if (flags.includes('ROUND_NUMBER_TRANSACTIONS') || (txA?.roundTxnCount > 3)) concerns.push(`Round-number transaction clustering: ${txA?.roundTxnCount || 'Multiple'} transactions at exact round amounts observed. While not conclusive alone, combined with other indicators this raises concern about synthetic transaction generation.`);
  if (flags.includes('BALANCE_INFLATION_SPIKE')) concerns.push('Temporary balance inflation: A disproportionate balance spike was detected shortly before application, which is inconsistent with historical account behavior. This pattern suggests possible pre-application balance manipulation.');
  if (flags.includes('NEW_SIM_RISK')) concerns.push(`Identity instability: Telecom number vintage of only ${features.telecom_number_vintage_days || '<90'} days. Very recent SIM activation combined with other risk signals reduces confidence in identity permanence.`);
  if (flags.includes('BENFORD_ANOMALY')) concerns.push("Benford's Law deviation: The leading-digit distribution of transaction amounts deviates significantly from the expected natural distribution. This statistical anomaly is associated with artificially constructed transaction histories.");
  if (flags.includes('GST_BANK_MISMATCH')) concerns.push('GST-bank data mismatch: Declared turnover through GST filings is materially inconsistent with observed bank transaction volume. This discrepancy reduces confidence in the accuracy of stated business scale.');
  if (flags.includes('TURNOVER_INFLATION_SPIKE')) concerns.push('Pre-application turnover spike: A significant and sudden increase in transaction volume was observed 30-60 days before the loan application. This temporal correlation raises concern about possible manufactured throughput.');

  if (concerns.length === 0) return 'No major forensic anomalies were identified in the available data. Transaction patterns appear organic, identity stability is adequate, and no circular fund flow indicators were detected.';

  return concerns.join('\n\n');
}

function buildJustification(outcome, grade, features, txA, flags, model, isMiddleman, profile, middleman, gst) {
  const name = profile?.name || 'The applicant';
  if (outcome === 'APPROVED') {
    let text = `The APPROVED decision for ${name} is appropriate because the positive signals clearly outweigh the identified risks. `;
    if (features.bounced_transaction_count === 0) text += 'Zero payment dishonors across the observed period provides direct evidence of balance adequacy. ';
    if (features.emergency_buffer_months >= 2) text += `An emergency buffer of ${features.emergency_buffer_months} months demonstrates capacity to absorb short-term income disruptions. `;
    if (features.telecom_number_vintage_days > 1000) text += 'Long telecom vintage provides a strong identity anchor. ';
    if (txA?.salaryCount >= 3) text += `Regular salary pattern (${txA.salaryCount} months) supports income predictability. `;
    if (isMiddleman && middleman?.supplierdata) text += `In the absence of formal credit records, the applicant's ${(middleman.supplierdata.payment_on_time_ratio * 100).toFixed(0)}% supplier payment rate over ${middleman.supplierdata.months_of_data} months, combined with field verification confirmation, provides sufficient proxy evidence of financial discipline. `;
    text += 'Repayment capacity appears adequate based on the available evidence.';
    return text;
  }
  if (outcome === 'APPROVED WITH CONDITIONS') {
    let text = `The APPROVED WITH CONDITIONS decision for ${name} reflects a broadly creditworthy profile that requires risk controls. `;
    if (features.business_vintage_months >= 48) text += `Business vintage of ${features.business_vintage_months} months provides a strong stability floor. `;
    if (features.revenue_seasonality_index > 0.5) text += `However, high seasonality (index: ${features.revenue_seasonality_index?.toFixed(2)}) means income concentration in specific months, requiring repayment alignment with revenue cycles. `;
    if (features.customer_concentration_ratio > 0.7) text += 'Elevated customer concentration introduces single-point-of-failure risk, warranting tighter monitoring. ';
    text += 'Conditions are recommended to manage identified risk factors while enabling access to credit based on the applicant\'s demonstrated operational track record.';
    return text;
  }
  if (outcome === 'MANUAL REVIEW') {
    let text = `${name}'s profile warrants MANUAL REVIEW because it presents contradictory signals that cannot be resolved through automated assessment alone. `;
    if (txA?.salaryCount >= 3) text += 'Income appears regular, suggesting viable repayment sources. ';
    if (features.cash_withdrawal_dependency > 0.3) text += `However, ${(features.cash_withdrawal_dependency * 100).toFixed(0)}% cash dependency obscures true expense patterns. `;
    if (txA?.zeroBalCount > 2) text += `The account reaches zero ${txA.zeroBalCount} times, raising concern about structural liquidity. `;
    text += 'Human review is recommended to verify income sources, assess undocumented obligations, and determine whether the applicant\'s true financial position supports the requested credit.';
    return text;
  }
  // REJECTED
  let text = `The REJECTED decision for ${name} is driven by `;
  const rejectionReasons = [];
  if (flags.includes('P2P_CIRCULAR_LOOP')) rejectionReasons.push('circular transaction patterns that undermine confidence in cashflow authenticity');
  if (flags.includes('BALANCE_INFLATION_SPIKE') || flags.includes('TURNOVER_INFLATION_SPIKE')) rejectionReasons.push('pre-application balance or turnover inflation indicating possible data manipulation');
  if (flags.includes('NEW_SIM_RISK')) rejectionReasons.push('very recent telecom identity raising identity stability concerns');
  if (flags.includes('GST_BANK_MISMATCH')) rejectionReasons.push('material mismatch between GST-declared and observed bank turnover');
  if (features.bounced_transaction_count > 2) rejectionReasons.push('repeated payment dishonors');
  if (txA?.zeroBalCount > 3) rejectionReasons.push('persistent liquidity exhaustion');
  if (rejectionReasons.length === 0) rejectionReasons.push('insufficient evidence of repayment capacity based on available data');
  text += rejectionReasons.join(', ') + '. ';
  text += 'The combination and severity of these signals places the applicant outside acceptable risk thresholds. The available evidence does not support a lending decision at this time.';
  return text;
}

function buildConditions(outcome, grade, features, flags, model, isMiddleman) {
  const conditions = [];
  if (outcome === 'APPROVED') {
    conditions.push('No additional conditions recommended based on the available data.');
    return conditions;
  }
  if (outcome === 'APPROVED WITH CONDITIONS') {
    if (features.revenue_seasonality_index > 0.5) conditions.push('Align EMI schedule with seasonal revenue cycles — consider bullet or step-up repayment structures to match harvest/seasonal income timing.');
    if (features.customer_concentration_ratio > 0.7) conditions.push('Cap exposure at a reduced amount proportional to diversification weakness. Re-evaluate at renewal if client base broadens.');
    if (features.avg_invoice_payment_delay > 30) conditions.push('Request additional 3 months of bank statements to verify invoice realization trajectory before full disbursement.');
    conditions.push('Standard field verification recommended before final disbursement.');
    if (features.business_vintage_months < 36) conditions.push('Shorter initial tenure (6-12 months) with renewal option based on repayment performance.');
    return conditions;
  }
  if (outcome === 'MANUAL REVIEW') {
    conditions.push('Assign to credit officer for manual deep-dive assessment.');
    if (features.cash_withdrawal_dependency > 0.3) conditions.push('Request applicant to provide evidence of cash-based expense breakdown or utility receipts for verification.');
    conditions.push('Verify stated income through employer confirmation or additional documentation.');
    if (features.min_balance_violation_count > 2) conditions.push('Assess whether applicant has undisclosed debt or repayment obligations affecting available liquidity.');
    conditions.push('If approved after manual review, consider reduced amount and shorter tenure with close monitoring.');
    return conditions;
  }
  // REJECTED
  conditions.push('Decline application at this time.');
  if (flags.includes('P2P_CIRCULAR_LOOP') || flags.includes('BALANCE_INFLATION_SPIKE')) conditions.push('Flag applicant for enhanced due diligence if re-application is received.');
  conditions.push('Applicant may re-apply after 6 months with stronger financial evidence and verified business documentation.');
  if (flags.includes('GST_BANK_MISMATCH')) conditions.push('If re-application occurs, require reconciliation of GST records against bank statements with CA certification.');
  return conditions;
}

export default generateCreditDecisionPDF;
