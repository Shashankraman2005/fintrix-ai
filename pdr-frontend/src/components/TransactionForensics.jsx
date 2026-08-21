import { useRef, useEffect, useMemo } from 'react';

// ── Detect suspicious transactions ───────────────────────────
function annotate(transactions) {
  if (!transactions?.length) return [];

  const avgCredit =
    transactions.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0) /
    (transactions.filter(t => t.amount > 0).length || 1);

  // Find circular pairs: credit from entity X then debit to same X within 3 days, ≥78% amount match
  const circularIndices = new Set();
  for (let i = 0; i < transactions.length; i++) {
    const tx = transactions[i];
    if (tx.amount <= 0) continue;
    const creditorKey = extractEntity(tx.narration);
    if (!creditorKey) continue;
    for (let j = i + 1; j < transactions.length; j++) {
      const tx2 = transactions[j];
      if (tx2.amount >= 0) continue;
      const daysDiff = (new Date(tx2.date) - new Date(tx.date)) / 86400000;
      if (daysDiff > 3) break;
      const debtorKey = extractEntity(tx2.narration);
      if (
        debtorKey &&
        debtorKey === creditorKey &&
        Math.abs(tx2.amount) / tx.amount >= 0.78
      ) {
        circularIndices.add(i);
        circularIndices.add(j);
      }
    }
  }

  return transactions.map((tx, idx) => {
    const flags = [];
    const abs = Math.abs(tx.amount);

    if (circularIndices.has(idx)) flags.push('circular');
    if (/bounce|chg/i.test(tx.narration)) flags.push('bounce');
    if (abs >= 10000 && abs % 1000 === 0) flags.push('round');
    if (tx.amount > 0 && tx.amount > avgCredit * 3.5) flags.push('spike');

    return { ...tx, flags };
  });
}

function extractEntity(narration = '') {
  // Strip common prefixes to get the counterparty name
  return narration
    .replace(/^(UPI TRANSFER FROM|UPI TRANSFER TO|NEFT|IMPS|UPI|RTGS|CHEQUE)\s+/i, '')
    .replace(/\s+(PAYMENT|INVOICE|TRANSFER|REF\s+\S+)$/i, '')
    .trim()
    .toUpperCase()
    .slice(0, 30);
}

const getFlagMeta = (isDark) => ({
  circular: { color: isDark ? '#f87171' : '#ef4444', bg: isDark ? 'rgba(239, 68, 68, 0.15)' : '#fef2f2', label: 'Circular Loop', icon: 'sync' },
  bounce:   { color: isDark ? '#fb923c' : '#f97316', bg: isDark ? 'rgba(249, 115, 22, 0.15)' : '#fff7ed', label: 'Bounce Charge', icon: 'money_off' },
  round:    { color: isDark ? '#facc15' : '#eab308', bg: isDark ? 'rgba(234, 179, 8, 0.15)' : '#fefce8', label: 'Round Number', icon: 'toll' },
  spike:    { color: isDark ? '#a78bfa' : '#8b5cf6', bg: isDark ? 'rgba(139, 92, 246, 0.15)' : '#f5f3ff', label: 'Income Spike', icon: 'trending_up' },
});

const rowBg = (flags, isDark) => {
  if (flags.includes('circular')) return isDark ? 'rgba(239, 68, 68, 0.08)' : '#fef2f2';
  if (flags.includes('bounce'))   return isDark ? 'rgba(249, 115, 22, 0.08)' : '#fff7ed';
  if (flags.includes('round'))    return isDark ? 'rgba(234, 179, 8, 0.08)' : '#fefce8';
  if (flags.includes('spike'))    return isDark ? 'rgba(139, 92, 246, 0.08)' : '#f5f3ff';
  return 'transparent';
};

export const FRAUD_FLAGS = ['P2P_CIRCULAR_LOOP', 'ROUND_NUMBER_TRANSACTIONS',
  'TURNOVER_INFLATION_SPIKE', 'BENFORD_ANOMALY', 'GST_BANK_MISMATCH',
  'BALANCE_INFLATION_SPIKE', 'HIGH_CASH_DEPENDENCY', 'MIN_BALANCE_VIOLATIONS',
  'LATE_UTILITY_PAYMENTS', 'NEW_SIM_RISK'];

// ── Main component ────────────────────────────────────────────
export default function TransactionForensics({ transactions, isDark = false }) {
  const chartRef = useRef(null);

  const annotated = useMemo(() => annotate(transactions || []), [transactions]);

  useEffect(() => {
    if (!annotated.length || !chartRef.current || !window.Chart) return;
    if (chartRef.current.chartInstance) chartRef.current.chartInstance.destroy();

    const labels = annotated.map(t => {
      const d = new Date(t.date);
      return `${d.getDate()}/${d.getMonth() + 1}`;
    });

    const normalCredit  = annotated.map(t => (t.amount > 0 && !t.flags.length) ? t.amount : 0);
    const normalDebit   = annotated.map(t => (t.amount < 0 && !t.flags.includes('circular') && !t.flags.includes('bounce')) ? Math.abs(t.amount) : 0);
    const circularTx    = annotated.map(t => t.flags.includes('circular') ? Math.abs(t.amount) : 0);
    const spikeTx       = annotated.map(t => (t.flags.includes('spike') && !t.flags.includes('circular')) ? t.amount : 0);
    const bounceTx      = annotated.map(t => t.flags.includes('bounce') ? Math.abs(t.amount) : 0);

    const ctx = chartRef.current.getContext('2d');
    chartRef.current.chartInstance = new window.Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Normal Credit',  data: normalCredit, backgroundColor: '#22c55e', borderRadius: 2 },
          { label: 'Normal Debit',   data: normalDebit,  backgroundColor: '#94a3b8', borderRadius: 2 },
          { label: '⚠ Circular Tx', data: circularTx,   backgroundColor: '#ef4444', borderRadius: 2 },
          { label: '⚠ Income Spike', data: spikeTx,      backgroundColor: '#8b5cf6', borderRadius: 2 },
          { label: '⚠ Bounce',       data: bounceTx,     backgroundColor: '#f97316', borderRadius: 2 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 10, font: { size: 11 }, color: '#6b7280' } },
          tooltip: {
            mode: 'index',
            callbacks: { label: ctx => `${ctx.dataset.label}: ₹${(ctx.raw / 1000).toFixed(1)}k` },
          },
        },
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { font: { size: 9 }, color: '#94a3b8' } },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: { font: { size: 10 }, color: '#94a3b8', callback: v => '₹' + (v / 1000).toFixed(0) + 'k' },
            grid: { color: 'rgba(0,0,0,0.05)' },
          },
        },
      },
    });
  }, [annotated]);

  // Early return AFTER all hooks
  if (!transactions?.length) return null;

  const circularCount = annotated.filter(t => t.flags.includes('circular')).length;
  const bounceCount   = annotated.filter(t => t.flags.includes('bounce')).length;
  const roundCount    = annotated.filter(t => t.flags.includes('round')).length;
  const spikeCount    = annotated.filter(t => t.flags.includes('spike')).length;

  const summaryCards = [
    { key: 'circular', count: circularCount,  label: 'Circular transactions',  desc: 'Money sent back to same entity within 3 days' },
    { key: 'bounce',   count: bounceCount,    label: 'Bounce charges',          desc: 'Payment failures on account' },
    { key: 'round',    count: roundCount,     label: 'Round-number transfers',  desc: 'Exact multiples of ₹1,000 — artificial pattern' },
    { key: 'spike',    count: spikeCount,     label: 'Income spikes',           desc: 'Credit >3.5× average monthly income' },
  ].filter(c => c.count > 0);

  const totalFlagged = summaryCards.reduce((s, c) => s + c.count, 0);

  return (
    <div className="r-section">
      {/* Header */}
      <h2 className="r-section-title">
        Transaction Forensics
        {totalFlagged > 0 ? (
          <span className="r-section-badge" style={{ background: isDark ? 'rgba(153, 27, 27, 0.2)' : '#fee2e2', color: isDark ? '#f87171' : '#991b1b' }}>
            {totalFlagged} flagged transactions
          </span>
        ) : (
          <span className="r-section-badge" style={{ background: isDark ? 'rgba(22, 101, 52, 0.2)' : '#dcfce7', color: isDark ? '#4ade80' : '#166534' }}>
            All clean
          </span>
        )}
      </h2>
      <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20, lineHeight: 1.6 }}>
        {totalFlagged > 0
          ? 'Each transaction below is annotated with the signal it triggered. Red rows directly influenced the decision. Report generated from raw bank statement data — no manual input.'
          : 'No suspicious patterns detected across all transactions. Each entry is shown below for full transparency.'}
      </p>

      {/* Signal summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
        {summaryCards.map(card => {
          const meta = getFlagMeta(isDark)[card.key];
          return (
            <div key={card.key} style={{
              background: meta.bg,
              border: `1px solid ${meta.color}30`,
              borderLeft: `4px solid ${meta.color}`,
              borderRadius: 10,
              padding: '14px 16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: meta.color }}>{meta.icon}</span>
                <span style={{ fontSize: 22, fontWeight: 800, color: meta.color }}>{card.count}</span>
              </div>
              <div style={{ fontSize: 12, fontWeight: 700, color: isDark ? '#f8fafc' : '#0f172a', marginBottom: 2 }}>{card.label}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>{card.desc}</div>
            </div>
          );
        })}
      </div>

      {/* Stacked bar chart */}
      <div style={{
        background: isDark ? '#1e293b' : '#fff',
        border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
        borderRadius: 12,
        padding: '16px 20px',
        marginBottom: 24,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: isDark ? '#f8fafc' : '#0f172a', marginBottom: 12 }}>
          Transaction Timeline — Flagged vs Normal
        </div>
        <div style={{ height: 200 }}>
          <canvas ref={chartRef} />
        </div>
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 8 }}>
          Red bars = circular fund flows. Normal credits shown in green. Chart uses absolute values for debits.
        </div>
      </div>

      {/* Annotated transaction table */}
      <div style={{ overflowX: 'auto', borderRadius: 12, border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}` }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: isDark ? '#0f172a' : '#f8fafc', borderBottom: `2px solid ${isDark ? '#334155' : '#e2e8f0'}` }}>
              {['Date', 'Narration', 'Amount', 'Balance', 'Fraud Signal'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 700, color: isDark ? '#cbd5e1' : '#475569', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {annotated.map((tx, idx) => {
              const isClean = tx.flags.length === 0;
              const bg = rowBg(tx.flags, isDark);
              return (
                <tr key={idx} style={{ background: bg, borderBottom: `1px solid ${isDark ? '#1e293b' : '#f1f5f9'}` }}>
                  <td style={{ padding: '9px 14px', color: '#64748b', whiteSpace: 'nowrap' }}>{tx.date}</td>
                  <td style={{ padding: '9px 14px', color: isClean ? (isDark ? '#cbd5e1' : '#475569') : (isDark ? '#f8fafc' : '#0f172a'), fontWeight: isClean ? 400 : 600, maxWidth: 280 }}>
                    {tx.narration}
                  </td>
                  <td style={{
                    padding: '9px 14px',
                    fontWeight: 700,
                    whiteSpace: 'nowrap',
                    color: tx.flags.includes('circular') ? (isDark ? '#f87171' : '#ef4444')
                         : tx.flags.includes('spike') ? (isDark ? '#a78bfa' : '#8b5cf6')
                         : tx.amount > 0 ? (isDark ? '#4ade80' : '#16a34a') : (isDark ? '#cbd5e1' : '#475569'),
                  }}>
                    {tx.amount > 0 ? '+' : ''}₹{Math.abs(tx.amount).toLocaleString('en-IN')}
                  </td>
                  <td style={{ padding: '9px 14px', color: '#64748b', whiteSpace: 'nowrap' }}>
                    ₹{tx.balance?.toLocaleString('en-IN') ?? '—'}
                  </td>
                  <td style={{ padding: '9px 14px' }}>
                    {tx.flags.length > 0 ? (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {tx.flags.map(f => {
                          const m = getFlagMeta(isDark)[f];
                          return (
                            <span key={f} style={{
                              background: m.bg,
                              color: m.color,
                              border: `1px solid ${m.color}40`,
                              borderRadius: 20,
                              padding: '2px 8px',
                              fontSize: 10,
                              fontWeight: 700,
                              whiteSpace: 'nowrap',
                            }}>
                              {m.label}
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      <span style={{ color: '#94a3b8', fontSize: 11 }}>Clean</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 12 }}>
        * Circular loop detection: same counterparty, credit→debit within 3 days, ≥78% amount match.
        Round-number flag: transfers ≥₹10,000 in exact multiples of ₹1,000.
        Spike flag: single credit &gt;3.5× average monthly income.
      </p>
    </div>
  );
}
