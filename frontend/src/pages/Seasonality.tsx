import { useMemo, useState } from 'react';
import industryData from '../data/industry-seasonality.json';
import etfReturnData from '../data/etf-nport-returns.json';
import './Seasonality.css';

type Industry = { code: string; name: string; emoji: string; examples: string; searchTerms?: string; proxy?: boolean };
type MonthlyRow = [number, ...number[]];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const INDUSTRIES: Industry[] = [
  { code: 'Agric', name: 'Agriculture', emoji: '🌾', examples: 'Archer-Daniels-Midland · Bunge' },
  { code: 'Food', name: 'Food products', emoji: '🍎', examples: 'Kraft Heinz · General Mills' },
  { code: 'Soda', name: 'Candy & soda', emoji: '🥤', examples: 'Coca-Cola · PepsiCo' },
  { code: 'Beer', name: 'Beer & liquor', emoji: '🍺', examples: 'Anheuser-Busch · Molson Coors' },
  { code: 'Smoke', name: 'Tobacco', emoji: '🚬', examples: 'Philip Morris · Altria' },
  { code: 'Toys', name: 'Toys', emoji: '🧸', examples: 'Mattel · Hasbro' },
  { code: 'Fun', name: 'Recreation', emoji: '🎮', examples: 'Electronic Arts · Take-Two' },
  { code: 'Books', name: 'Printing & publishing', emoji: '📚', examples: 'News Corp · New York Times' },
  { code: 'Hshld', name: 'Consumer goods', emoji: '🧴', examples: 'Procter & Gamble · Colgate-Palmolive' },
  { code: 'Clths', name: 'Apparel', emoji: '👕', examples: 'Nike · Ralph Lauren' },
  { code: 'Hlth', name: 'Healthcare', emoji: '🧬', examples: 'UnitedHealth · CVS Health' },
  { code: 'MedEq', name: 'Medical equipment', emoji: '🩺', examples: 'Medtronic · Stryker' },
  { code: 'Drugs', name: 'Pharmaceutical products', emoji: '💊', examples: 'Johnson & Johnson · Eli Lilly' },
  { code: 'Chems', name: 'Chemicals', emoji: '⚗️', examples: 'Linde · Dow' },
  { code: 'Rubbr', name: 'Rubber & plastics', emoji: '🛞', examples: 'Goodyear · DuPont' },
  { code: 'Txtls', name: 'Textiles', emoji: '🧵', examples: 'Levi Strauss · V.F. Corporation' },
  { code: 'BldMt', name: 'Construction materials', emoji: '🧱', examples: 'Vulcan Materials · Martin Marietta' },
  { code: 'Cnstr', name: 'Construction', emoji: '🏗️', examples: 'Caterpillar · United Rentals' },
  { code: 'Steel', name: 'Steel works', emoji: '🏭', examples: 'Nucor · Steel Dynamics' },
  { code: 'FabPr', name: 'Fabricated products', emoji: '🔩', examples: 'Parker-Hannifin · Cummins' },
  { code: 'Mach', name: 'Machinery', emoji: '⚙️', examples: 'Deere · Illinois Tool Works' },
  { code: 'ElcEq', name: 'Electrical equipment', emoji: '🔌', examples: 'Eaton · Emerson Electric' },
  { code: 'Autos', name: 'Automobiles & trucks', emoji: '🚗', examples: 'General Motors · Ford' },
  { code: 'Aero', name: 'Aircraft', emoji: '✈️', examples: 'Boeing · RTX' },
  { code: 'Ships', name: 'Shipbuilding & railroad equipment', emoji: '🚆', examples: 'Huntington Ingalls · Wabtec' },
  { code: 'Guns', name: 'Defense', emoji: '🛡️', examples: 'Lockheed Martin · Northrop Grumman' },
  { code: 'Gold', name: 'Precious metals', emoji: '🥇', examples: 'Newmont · Barrick Mining' },
  { code: 'Mines', name: 'Mining', emoji: '⛏️', examples: 'Freeport-McMoRan · Southern Copper' },
  { code: 'Coal', name: 'Coal', emoji: '⚫', examples: 'Peabody Energy · Alpha Metallurgical' },
  { code: 'Oil', name: 'Oil & natural gas', emoji: '🛢️', examples: 'Exxon Mobil · Chevron' },
  { code: 'Util', name: 'Utilities', emoji: '⚡', examples: 'NextEra Energy · Duke Energy' },
  { code: 'Telcm', name: 'Telecommunications', emoji: '📡', examples: 'AT&T · Verizon' },
  { code: 'PerSv', name: 'Personal services', emoji: '🧑‍💼', examples: 'H&R Block · Service Corp. International' },
  { code: 'BusSv', name: 'Business services', emoji: '🧾', examples: 'Accenture · Waste Management' },
  { code: 'Hardw', name: 'Computers & hardware', emoji: '🖥️', examples: 'IBM · Hewlett Packard Enterprise' },
  { code: 'Softw', name: 'Software', emoji: '💾', examples: 'Microsoft · Oracle' },
  { code: 'Chips', name: 'Semiconductors', emoji: '🔬', examples: 'NVIDIA · Texas Instruments' },
  { code: 'LabEq', name: 'Measuring & control equipment', emoji: '🧪', examples: 'Agilent · Keysight Technologies' },
  { code: 'Paper', name: 'Paper & packaging', emoji: '📦', examples: 'International Paper · Packaging Corp.' },
  { code: 'Boxes', name: 'Shipping containers', emoji: '🚢', examples: 'Packaging Corp. · Greif' },
  { code: 'Trans', name: 'Transportation', emoji: '🚚', examples: 'UPS · FedEx' },
  { code: 'Whlsl', name: 'Wholesale', emoji: '🏬', examples: 'Costco · W.W. Grainger' },
  { code: 'Rtail', name: 'Retail', emoji: '🛍️', examples: 'Walmart · Target' },
  { code: 'Meals', name: 'Restaurants & hotels', emoji: '🍽️', examples: "McDonald's · Marriott" },
  { code: 'Banks', name: 'Banking', emoji: '🏦', examples: 'JPMorgan Chase · Bank of America' },
  { code: 'Insur', name: 'Insurance', emoji: '☂️', examples: 'Progressive · Allstate' },
  { code: 'RlEst', name: 'Real estate', emoji: '🏢', examples: 'CBRE · Prologis' },
  { code: 'Fin', name: 'Trading & other finance', emoji: '💹', examples: 'CME Group · Charles Schwab' },
  { code: 'Other', name: 'Other industries', emoji: '🧩', examples: '3M · Honeywell' },
];
const MARKET: Industry = { code: 'Market', name: 'Overall U.S. market', emoji: '🌐', examples: 'Broad U.S. listed equities', searchTerms: 'overall market benchmark' };
const MARKET_INDEX = INDUSTRIES.length;

const THEME_EMOJI: Record<string, string> = { AI: '🤖', Robotics: '🦾', Quantum: '⚛️', Nuclear: '☢️', Renewable: '🌱' };
const THEME_SERIES = etfReturnData.series.map((series) => ({
  code: series.code,
  name: series.name,
  emoji: THEME_EMOJI[series.code] ?? '📈',
  examples: `${series.ticker} ETF proxy · ${series.periodStart}–${series.periodEnd}`,
  searchTerms: `${series.name} ${series.ticker} ${series.fundName}`,
  proxy: true,
}));
const SERIES = [...INDUSTRIES, MARKET, ...THEME_SERIES];

const rows = industryData.rows as MonthlyRow[];
const HISTORICAL_ROWS = rows.filter((row) => Math.floor(row[0] / 100) <= industryData.completeCalendarYearsThrough);
const years = Array.from(new Set(rows.map((row) => Math.floor(row[0] / 100))));
const SCALE = 4;

function themeFor(code: string) {
  return etfReturnData.series.find((series) => series.code === code);
}

function themeReturn(code: string, period: number) {
  const observation = themeFor(code)?.returns.find((item) => item.period === period);
  return observation ? observation.value : Number.NaN;
}

function themeObservation(code: string, period: number) {
  return themeFor(code)?.returns.find((item) => item.period === period);
}

function selectedReturn(row: MonthlyRow, industry: Industry) {
  if (industry.proxy) return themeReturn(industry.code, row[0]);
  const index = industry.code === MARKET.code ? MARKET_INDEX : industryData.industryCodes.indexOf(industry.code);
  return returnAt(row, index);
}

function returnAt(row: MonthlyRow, industryIndex: number) {
  return row[industryIndex + 1];
}

function formatReturn(value: number) {
  const rounded = Number(value.toFixed(2));
  return `${rounded > 0 ? '+' : ''}${rounded.toFixed(2)}%`;
}

function heatColor(value: number) {
  const intensity = Math.min(Math.abs(value) / SCALE, 1);
  if (value > 0) return `rgba(46, 204, 136, ${0.12 + intensity * 0.55})`;
  if (value < 0) return `rgba(255, 91, 105, ${0.12 + intensity * 0.55})`;
  return 'rgba(174, 191, 212, 0.09)';
}

function buildSeries(industry: Industry, yearFilter: number | 'all') {
  const chosenRows = yearFilter === 'all' ? HISTORICAL_ROWS : rows.filter((row) => Math.floor(row[0] / 100) === yearFilter);
  const annual = new Map<number, number[]>();
  chosenRows.forEach((row) => {
    const year = Math.floor(row[0] / 100);
    const month = (row[0] % 100) - 1;
    const values = annual.get(year) ?? Array(12).fill(Number.NaN);
    values[month] = selectedReturn(row, industry);
    annual.set(year, values);
  });
  if (industry.proxy) {
    const theme = themeFor(industry.code);
    theme?.returns.forEach(({ period, value }) => {
      const year = Math.floor(period / 100);
      if ((yearFilter === 'all' && year > industryData.completeCalendarYearsThrough) || (yearFilter !== 'all' && year !== yearFilter)) return;
      const month = (period % 100) - 1;
      const values = annual.get(year) ?? Array(12).fill(Number.NaN);
      values[month] = value;
      annual.set(year, values);
    });
  }
  return [...annual.entries()].sort(([a], [b]) => a - b).map(([year, values]) => ({ year, values })).filter(({ values }) => values.some(Number.isFinite));
}

function SeasonalityChart({
  series,
  monthlyAverages,
  monthlyAverageLabel,
  focusedYear,
  onToggleYear,
}: {
  series: Array<{ year: number; values: number[] }>;
  monthlyAverages: number[];
  monthlyAverageLabel: string;
  focusedYear: number | null;
  onToggleYear: (year: number) => void;
}) {
  const width = 860;
  const height = 340;
  const left = 52;
  const right = 18;
  const top = 18;
  const bottom = 42;
  const allValues = series.flatMap((item) => item.values).filter(Number.isFinite);
  const maxAbs = Math.max(5, Math.ceil((Math.max(...allValues.map(Math.abs), 0) + 0.5) / 5) * 5);
  const x = (index: number) => left + (index * (width - left - right)) / 11;
  const y = (value: number) => top + ((maxAbs - value) * (height - top - bottom)) / (maxAbs * 2);
  const ticks = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs];

  return (
    <div className="seasonality-chart-wrap">
      <svg className="seasonality-chart" viewBox={`0 0 ${width} ${height}`} role="group" aria-label="Monthly returns by calendar year. Select a year below to highlight it.">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className={tick === 0 ? 'chart-zero' : 'chart-gridline'} />
            <text x={left - 8} y={y(tick) + 4} textAnchor="end" className="chart-axis-label">{tick.toFixed(0)}%</text>
          </g>
        ))}
        {MONTHS.map((month, index) => (
          <text key={month} x={x(index)} y={height - 13} textAnchor="middle" className="chart-axis-label">{month}</text>
        ))}
        {series.map((item, index) => {
          const points = item.values.flatMap((value, month) => Number.isFinite(value) ? [`${x(month)},${y(value)}`] : []).join(' ');
          const color = series.length === 1 ? '#8fc8ff' : `hsl(${(index * 137.508 + 205) % 360} 82% 72%)`;
          const focused = focusedYear === item.year;
          const observedValues = item.values.filter(Number.isFinite);
          const annualTotal = observedValues.reduce((growth, value) => growth * (1 + value / 100), 1) - 1;
          const lastMonth = item.values.reduce((last, value, month) => Number.isFinite(value) ? month : last, -1);
          const totalLabel = observedValues.length === 12 ? `calendar-year return ${formatReturn(annualTotal * 100)}` : `return through ${MONTHS[lastMonth]} ${formatReturn(annualTotal * 100)}`;
          return (
            <g key={item.year} className={focused ? 'chart-year-focused' : undefined}>
              <polyline
                points={points}
                fill="none"
                stroke={color}
                strokeWidth={focused ? 3.5 : series.length === 1 ? 3 : 1.5}
                strokeOpacity={focusedYear === null ? (series.length === 1 ? 1 : 0.66) : focused ? 1 : 0.16}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {item.values.flatMap((value, month) => Number.isFinite(value) ? [(() => {
                const monthMean = monthlyAverages[month];
                const difference = value - monthMean;
                const comparison = Number.isFinite(monthMean) ? `${monthlyAverageLabel} ${MONTHS[month]} mean: ${formatReturn(monthMean)}. Difference from monthly mean: ${difference > 0 ? '+' : ''}${difference.toFixed(2)} percentage points.` : 'No comparison average is available.';
                const pointSummary = `${item.year} ${MONTHS[month]}: ${formatReturn(value)}. ${comparison}`;
                return (
                  <circle
                    key={`${item.year}-${month}`}
                    className="chart-month-hit"
                    cx={x(month)}
                    cy={y(value)}
                    r={focused ? 7 : 5}
                    tabIndex={0}
                    aria-label={pointSummary}
                  >
                    <title>{pointSummary}</title>
                  </circle>
                );
              })()] : [])}
              {item.values.flatMap((value, month) => Number.isFinite(value) ? [(
                <circle
                  key={`dot-${item.year}-${month}`}
                  cx={x(month)}
                  cy={y(value)}
                  r={focused ? 2.8 : 2.2}
                  fill={color}
                  fillOpacity={focusedYear === null ? 0.72 : focused ? 1 : 0.13}
                  pointerEvents="none"
                />
              )] : [])}
              <title>{`${item.year}: compounded ${totalLabel}. Click its year below to highlight or restore all years.`}</title>
            </g>
          );
        })}
      </svg>
      <div className="seasonality-year-legend" aria-label="Chart year colors">
        {series.map((item, index) => (
          <button
            key={item.year}
            type="button"
            aria-pressed={focusedYear === item.year}
            aria-label={focusedYear === item.year ? `Unfocus ${item.year}; show all years equally` : `Focus ${item.year}; fade the other years`}
            className={focusedYear !== null && focusedYear !== item.year ? 'seasonality-year-muted' : undefined}
            onClick={() => onToggleYear(item.year)}
          >
            <i style={{ background: series.length === 1 ? '#8fc8ff' : `hsl(${(index * 137.508 + 205) % 360} 82% 72%)` }} />
            {item.year}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Seasonality() {
  const [yearFilter, setYearFilter] = useState<number | 'all'>('all');
  const [focusedYear, setFocusedYear] = useState<number | null>(null);
  const [selectedCode, setSelectedCode] = useState(INDUSTRIES[0].code);
  const [query, setQuery] = useState('');
  const selected = SERIES.find((industry) => industry.code === selectedCode) ?? INDUSTRIES[0];

  const heatmap = useMemo(() => {
    const chosenRows = yearFilter === 'all' ? HISTORICAL_ROWS : rows.filter((row) => Math.floor(row[0] / 100) === yearFilter);
    return SERIES.map((industry) => {
      const values = MONTHS.map((_, month) => {
        const matching = chosenRows.filter((row) => row[0] % 100 === month + 1);
        const observations = matching.map((row) => selectedReturn(row as MonthlyRow, industry)).filter(Number.isFinite);
        return observations.length ? observations.reduce((total, value) => total + value, 0) / observations.length : Number.NaN;
      });
      return { industry, values };
    }).filter(({ industry }) => `${industry.name} ${industry.examples} ${industry.searchTerms ?? ''}`.toLowerCase().includes(query.trim().toLowerCase()));
  }, [yearFilter, query]);

  const chartSeries = useMemo(() => buildSeries(selected, yearFilter), [selected, yearFilter]);
  const periodReturns = chartSeries.flatMap((item) => item.values).filter(Number.isFinite);
  const average = periodReturns.length ? periodReturns.reduce((sum, value) => sum + value, 0) / periodReturns.length : 0;
  const monthlyAverages = useMemo(() => MONTHS.map((_, month) => {
    const matching = HISTORICAL_ROWS.filter((row) => row[0] % 100 === month + 1);
    const observations = matching.map((row) => selectedReturn(row, selected)).filter(Number.isFinite);
    return observations.length ? observations.reduce((sum, value) => sum + value, 0) / observations.length : Number.NaN;
  }), [selected]);
  const monthlyAverageLabel = selected.proxy ? 'available-history' : '30-year';
  const focusedSeries = chartSeries.find((item) => item.year === focusedYear);
  const focusedValues = focusedSeries?.values.filter(Number.isFinite) ?? [];
  const focusedMean = focusedValues.length ? focusedValues.reduce((sum, value) => sum + value, 0) / focusedValues.length : null;
  const focusedTotal = focusedValues.length ? (focusedValues.reduce((growth, value) => growth * (1 + value / 100), 1) - 1) * 100 : null;

  function toggleChartYear(year: number) {
    if (yearFilter !== 'all') {
      setYearFilter('all');
      setFocusedYear(year);
      return;
    }
    setFocusedYear((current) => current === year ? null : year);
  }

  return (
    <div className="seasonality-page">
      <header className="seasonality-header">
        <div>
          <p className="seasonality-kicker">Historical patterns · U.S. equities</p>
          <h2>Industry seasonality</h2>
          <p>Compare 49 official U.S. industries and the broad market across 30 years, plus five shorter-history ETF proxies for newer themes.</p>
        </div>
        <div className="seasonality-period-control">
          <div className="seasonality-period-readout">
            <span>Time period</span>
            <output>{yearFilter === 'all' ? 'All complete years · monthly average' : yearFilter === 2026 ? '2026 · official through Sep' : yearFilter}</output>
          </div>
          <input
            type="range"
            min={0}
            max={years.length}
            step={1}
            value={yearFilter === 'all' ? 0 : years.indexOf(yearFilter) + 1}
            onChange={(event) => {
              const index = Number(event.target.value);
              setFocusedYear(null);
              setYearFilter(index === 0 ? 'all' : years[index - 1]);
            }}
            aria-label="Choose all years or slide to a single year from 1996 to 2026"
            aria-valuetext={yearFilter === 'all' ? 'All years monthly average' : String(yearFilter)}
          />
          <div className="seasonality-slider-labels" aria-hidden="true"><span>All complete years · 1996</span><span>2026 · Sep</span></div>
        </div>
      </header>

      <div className="seasonality-stats">
        <div><strong>49 + market + 5</strong><span>industries / benchmark / ETF proxies</span></div>
        <div><strong>30 yrs</strong><span>official industry & market · 1996–2025</span></div>
        <div><strong>{rows.length}</strong><span>official months · Jan 1996–Sep 2026</span></div>
        <div><strong>{formatReturn(average)}</strong><span>{selected.name} mean monthly return</span></div>
      </div>

      <section className="seasonality-panel" aria-labelledby="seasonality-heatmap-title">
        <div className="seasonality-section-heading">
          <div>
            <h3 id="seasonality-heatmap-title">Monthly return heatmap</h3>
            <p>{yearFilter === 'all' ? 'Official series average across 1996–2025; thematic ETF proxies use only their SEC-filed available history.' : yearFilter === 2026 ? 'Official industries and market run through September. Thematic proxy rows stop at their latest public SEC filing; blank cells are unavailable.' : `Monthly returns during ${yearFilter}; blank cells indicate no reported observation for that series.`}</p>
          </div>
          <label className="seasonality-search">
            <span className="sr-only">Search industries, market, or example companies</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find industry, market, or company" />
          </label>
        </div>

        <div className="seasonality-heatmap" role="group" aria-label="Select a return series to inspect its monthly chart">
          <div className="seasonality-row seasonality-month-header" aria-hidden="true">
            <span className="seasonality-name-column">Industry / market / ETF proxy · series source</span>
            <div className="seasonality-month-cells">{MONTHS.map((month) => <span key={month} title={month}>{month}</span>)}</div>
          </div>
          {heatmap.map(({ industry, values }) => (
            <button
              type="button"
              className={`seasonality-row seasonality-industry-row ${industry.code === selectedCode ? 'selected' : ''}`}
              key={industry.code}
              aria-pressed={industry.code === selectedCode}
              onClick={() => setSelectedCode(industry.code)}
            >
              <span className="seasonality-name-column">
                <span className="seasonality-industry-name"><span aria-hidden="true">{industry.emoji}</span>{industry.name}</span>
                <span className="seasonality-examples">{industry.examples}</span>
              </span>
              <span className="seasonality-month-cells">
                {values.map((value, index) => (
                  <span
                    key={MONTHS[index]}
                    className="seasonality-cell"
                    style={Number.isFinite(value) ? { backgroundColor: heatColor(value) } : undefined}
                    title={Number.isFinite(value) ? `${industry.name} · ${MONTHS[index]} · ${formatReturn(value)}${yearFilter === 'all' ? ' monthly average' : ` in ${yearFilter}`}${industry.proxy ? yearFilter === 'all' ? ' · SEC-filed available-history average' : ` · Form N-PORT filed ${themeObservation(industry.code, yearFilter * 100 + index + 1)?.filedOn ?? 'date unavailable'}` : ''}` : `${industry.name} · ${MONTHS[index]} · no publicly reported observation`}
                    aria-label={`${MONTHS[index]} ${Number.isFinite(value) ? formatReturn(value) : 'no data'}`}
                  >
                    {Number.isFinite(value) ? Number(value.toFixed(1)).toFixed(1) : '—'}
                  </span>
                ))}
              </span>
            </button>
          ))}
          {heatmap.length === 0 && <p className="seasonality-empty">No industries match that search.</p>}
        </div>

        <div className="seasonality-scale" aria-label="Heatmap scale clipped at four percentage points">
          <span>Lower return</span><i className="scale-negative" /><span>−4%</span><i className="scale-neutral" /><span>0%</span><i className="scale-positive" /><span>+4% or higher</span><span>· colors clip at ±4%; cell labels round to 0.1%, hover for exact values</span>
        </div>
      </section>

      <section className="seasonality-panel seasonality-chart-panel" aria-labelledby="seasonality-chart-title">
        <div className="seasonality-section-heading">
          <div>
            <p className="seasonality-kicker">Selected return series</p>
            <h3 id="seasonality-chart-title"><span aria-hidden="true">{selected.emoji}</span> {selected.name}</h3>
            <p>{selected.examples}{!selected.proxy && selected.code !== MARKET.code && <span className="seasonality-illustrative"> (illustrative examples, not portfolio constituents)</span>}</p>
          </div>
          <div className="seasonality-average-badge">
            <strong>{formatReturn(focusedMean ?? average)}</strong>
            <span>{focusedYear ? `${focusedYear} mean monthly return` : 'mean monthly return'}<br />{focusedTotal === null ? 'over selected period' : `compounded year return ${formatReturn(focusedTotal)}`}</span>
          </div>
        </div>
        <p className="seasonality-chart-caption">
          {yearFilter === 'all'
            ? focusedYear
              ? `${focusedYear} is highlighted; other years are faded. Click ${focusedYear} again to restore all years. Hover or focus a point for its monthly return and comparison with the ${monthlyAverageLabel} monthly average.`
              : `Each line is one available calendar year. Click a year below to highlight it; click again to restore all lines. Hover or focus a point for its monthly return and ${monthlyAverageLabel} average.`
            : yearFilter === 2026 && selected.proxy
              ? `SEC-filed monthly total returns for ${selected.name} through ${themeFor(selected.code)?.periodEnd ?? 'latest filing'}. October is not yet reported in public filings.`
              : yearFilter === 2026
                ? 'Official industry and market total returns are available through September 2026; October onward awaits a source release.'
                : `Monthly total returns for ${yearFilter}. Hover the line for exact values.`}
        </p>
        <SeasonalityChart series={chartSeries} monthlyAverages={monthlyAverages} monthlyAverageLabel={monthlyAverageLabel} focusedYear={focusedYear} onToggleYear={toggleChartYear} />
      </section>

      <details className="seasonality-method">
        <summary>Data, method & limitations</summary>
        <p>
          Official industry source: <a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html" target="_blank" rel="noreferrer">Kenneth R. French Data Library · 49 Industry Portfolios</a>. Its `Chips` and `Softw` series provide the official semiconductor and software group returns. The portfolios classify U.S. stocks by SIC, reconstitute annually in June, and report value-weighted monthly returns. The overall market uses the <a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html" target="_blank" rel="noreferrer">Fama/French market return</a>, Mkt-RF + RF, for eligible U.S.-incorporated NYSE, AMEX, and NASDAQ stocks. These official series provide 30 complete years (1996–2025) plus 2026 through September. The French source has not yet published October 2026. The five themes below are ETF proxies, not official Fama/French industries or 30-year sector indexes. They use fund-reported monthly total returns from SEC Form N-PORT Item B.5. Coverage begins with the SEC's available public filings and ends at each ETF's latest filed month; the SEC filing cadence means October is not yet reported. Returns are percent, net fund returns, as filed. ETF names and strategies are set by fund issuers and may change; the theme labels summarize each proxy, not a uniform industry classification. CRSP data may be revised; SEC filings can be amended. Company examples are illustrative and do not establish portfolio membership.
        </p>
        <p className="seasonality-source-note">French source files: 49_Industry_Portfolios_CSV.zip and F-F_Research_Data_Factors_CSV.zip · CRSP database through September 2026 · retrieved 1 November 2026. Thematic funds: SEC EDGAR Form N-PORT Item B.5, SEC filings retrieved 1 November 2026. Copyright Eugene F. Fama and Kenneth R. French for the French source files.</p>
        <ul className="seasonality-proxy-sources">
          {etfReturnData.series.map((proxy) => <li key={proxy.code}><strong>{proxy.name} ({proxy.ticker})</strong>: {proxy.fundName}; SEC return coverage {proxy.periodStart}–{proxy.periodEnd}. <a href={proxy.sourceUrl} target="_blank" rel="noreferrer">SEC filings</a> · <a href={proxy.issuerUrl} target="_blank" rel="noreferrer">fund issuer</a>. The series ID is {proxy.seriesId}; {proxy.historicalFundNames.length > 1 ? `the filed fund name has also appeared as ${proxy.historicalFundNames.slice(0, -1).join(', ')}.` : 'the SEC filing name matches the fund currently listed.'} Each plotted month maps to Form N-PORT's month 1/2/3 return field and includes the accession and filed value in the dataset.</li>)}
        </ul>
      </details>
      <p className="seasonality-disclaimer">Historical seasonality is descriptive and may not persist. It is not a forecast, trading signal, or investment recommendation.</p>
    </div>
  );
}
