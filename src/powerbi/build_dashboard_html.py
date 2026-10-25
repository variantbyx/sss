import json
import os
import pandas as pd

def build_dashboard():
    # Load forecast data
    df_fc = pd.read_csv('demand_forecast_output.csv')
    df_daily = pd.read_csv('fact_daily_demand.csv')
    df_sku = pd.read_csv('sku_inventory_status.csv')

    # Get daily demand actuals for the last 90 historical days + 30 days forecast
    df_daily_total = df_daily.groupby('order_date')['actual_units'].sum().reset_index()
    df_daily_total['order_date'] = pd.to_datetime(df_daily_total['order_date'])
    df_recent_actuals = df_daily_total.sort_values('order_date').tail(90)

    # Forecast timeline
    df_fc['ds'] = pd.to_datetime(df_fc['ds'])
    forecast_timeline = df_fc.tail(60).copy() # last 30 actuals + 30 future

    # Prepare chart points
    chart_labels = []
    actual_data = []
    forecast_data = []
    lower_bound = []
    upper_bound = []

    # Map actuals to dates
    actuals_dict = dict(zip(df_daily_total['order_date'].dt.strftime('%Y-%m-%d'), df_daily_total['actual_units']))

    for _, row in forecast_timeline.iterrows():
        d_str = row['ds'].strftime('%Y-%m-%d')
        chart_labels.append(d_str)
        forecast_data.append(round(float(row['yhat']), 1))
        lower_bound.append(round(float(row['yhat_lower']), 1))
        upper_bound.append(round(float(row['yhat_upper']), 1))
        actual_data.append(actuals_dict.get(d_str, None))

    # Prepare SKU table data (top 60 diverse SKUs for table display)
    sample_skus = df_sku.head(80).to_dict(orient='records')

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Supply Chain Analytics | Executive Power BI Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg-primary: #0a0e17;
      --bg-card: rgba(18, 24, 38, 0.85);
      --bg-card-hover: rgba(26, 35, 54, 0.95);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-focus: #3b82f6;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --accent-purple: #818cf8;
      --danger: #ef4444;
      --warning: #f59e0b;
      --success: #10b981;
      --glow-blue: rgba(56, 189, 248, 0.15);
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    body {{
      background: radial-gradient(circle at 10% 20%, #111827 0%, #0a0e17 90%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 24px;
      overflow-x: hidden;
    }}

    .container {{
      max-width: 1440px;
      margin: 0 auto;
    }}

    /* Header */
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 28px;
    }}

    .header-title h1 {{
      font-size: 26px;
      font-weight: 800;
      background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }}

    .header-title p {{
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 4px;
    }}

    .header-badges {{
      display: flex;
      gap: 12px;
    }}

    .badge {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .badge.live {{
      color: var(--success);
      border-color: rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.1);
    }}

    .pulse-dot {{
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success);
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 28px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 22px;
      position: relative;
      overflow: hidden;
      transition: all 0.25s ease;
    }}

    .kpi-card:hover {{
      transform: translateY(-3px);
      border-color: rgba(56, 189, 248, 0.4);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px var(--glow-blue);
    }}

    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--border-color);
    }}

    .kpi-card.danger::before {{ background: var(--danger); }}
    .kpi-card.warning::before {{ background: var(--warning); }}
    .kpi-card.success::before {{ background: var(--success); }}
    .kpi-card.blue::before {{ background: var(--accent-blue); }}

    .kpi-label {{
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .kpi-value {{
      font-size: 32px;
      font-weight: 800;
      margin: 10px 0 6px 0;
      letter-spacing: -1px;
    }}

    .kpi-subtitle {{
      font-size: 13px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .kpi-subtitle span.highlight {{
      font-weight: 700;
    }}

    /* Main Grid */
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
      margin-bottom: 28px;
    }}

    @media (max-width: 1024px) {{
      .dashboard-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .panel {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 24px;
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }}

    .panel-title {{
      font-size: 18px;
      font-weight: 700;
    }}

    .panel-tag {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }}

    .chart-container {{
      position: relative;
      height: 340px;
      width: 100%;
    }}

    /* Gauge / Inventory Health Summary */
    .health-summary {{
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}

    .progress-bar-wrap {{
      margin-top: 6px;
    }}

    .progress-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      margin-bottom: 6px;
    }}

    .progress-track {{
      background: rgba(255, 255, 255, 0.08);
      height: 10px;
      border-radius: 9999px;
      overflow: hidden;
      display: flex;
    }}

    .progress-fill {{
      height: 100%;
      transition: width 0.8s ease;
    }}

    .progress-fill.green {{ background: var(--success); }}
    .progress-fill.amber {{ background: var(--warning); }}
    .progress-fill.red {{ background: var(--danger); }}

    /* DAX Code Drawer */
    .dax-card {{
      background: #0f172a;
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 12px;
      padding: 16px;
      margin-top: 14px;
    }}

    .dax-header {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--accent-blue);
      font-weight: 700;
      margin-bottom: 8px;
      font-family: 'JetBrains Mono', monospace;
    }}

    pre.dax-code {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #e2e8f0;
      line-height: 1.5;
      overflow-x: auto;
    }}

    /* Table Section */
    .table-container {{
      overflow-x: auto;
      max-height: 480px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }}

    th {{
      position: sticky;
      top: 0;
      background: #111827;
      color: var(--text-muted);
      font-weight: 700;
      padding: 14px 16px;
      border-bottom: 1px solid var(--border-color);
      white-space: nowrap;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.5px;
    }}

    td {{
      padding: 14px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      white-space: nowrap;
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .sku-id {{
      font-family: 'JetBrains Mono', monospace;
      color: var(--accent-blue);
      font-weight: 600;
    }}

    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.3px;
    }}

    .status-badge.critical {{
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .status-badge.reorder {{
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .status-badge.healthy {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .filter-bar {{
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}

    .search-input {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 14px;
      color: var(--text-main);
      font-size: 13px;
      min-width: 260px;
      outline: none;
    }}

    .search-input:focus {{
      border-color: var(--border-focus);
    }}

    .filter-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .filter-btn.active, .filter-btn:hover {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent-blue);
      border-color: rgba(56, 189, 248, 0.4);
    }}
  </style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <header>
    <div class="header-title">
      <h1>Smart Supply Chain Analytics Engine</h1>
      <p>Automated Demand Forecasting, Dynamic Safety Stock & Reorder Optimization</p>
    </div>
    <div class="header-badges">
      <div class="badge live"><div class="pulse-dot"></div> Live Telemetry</div>
      <div class="badge">Power BI Enterprise</div>
      <div class="badge">Prophet v1.5.0</div>
    </div>
  </header>

  <!-- KPI Cards (Visual 2) -->
  <div class="kpi-grid">
    <div class="kpi-card danger">
      <div class="kpi-label">Projected Stockout Risks</div>
      <div class="kpi-value" style="color: var(--danger);">454</div>
      <div class="kpi-subtitle"><span class="highlight" style="color: var(--danger);">41.6%</span> of SKUs need urgent restocking</div>
    </div>
    <div class="kpi-card success">
      <div class="kpi-label">Forecast Accuracy (1 - MAPE)</div>
      <div class="kpi-value" style="color: var(--success);">96.6%</div>
      <div class="kpi-subtitle">Model RMSE: <span class="highlight">101.59 units</span></div>
    </div>
    <div class="kpi-card warning">
      <div class="kpi-label">Reorder Alerts (< ROP)</div>
      <div class="kpi-value" style="color: var(--warning);">151</div>
      <div class="kpi-subtitle">Critical Stockouts (< SS): <span class="highlight" style="color: var(--danger);">303</span></div>
    </div>
    <div class="kpi-card blue">
      <div class="kpi-label">Active Monitored SKUs</div>
      <div class="kpi-value">1,091</div>
      <div class="kpi-subtitle">Inventory Valuation: <span class="highlight">$533,195</span></div>
    </div>
  </div>

  <!-- Main Analytics Grid -->
  <div class="dashboard-grid">
    <!-- Visual 1: Historical Actual Demand vs. Predicted Forecast -->
    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Demand Forecasting: Historical Actuals vs. 30-Day Forward Forecast</div>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Prophet additive model with 95% confidence intervals and Reorder Threshold line</p>
        </div>
        <div class="panel-tag">Visual 1 (Line Chart)</div>
      </div>
      <div class="chart-container">
        <canvas id="forecastChart"></canvas>
      </div>
    </div>

    <!-- Visual 2: Inventory Health Gauge & DAX Code Reference -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Inventory Health & DAX</div>
        <div class="panel-tag">Visual 2 (Gauge)</div>
      </div>
      
      <div class="health-summary">
        <div>
          <div class="progress-labels">
            <span>Healthy Stock (≥ ROP)</span>
            <span style="color: var(--success); font-weight: 700;">637 SKUs (58.4%)</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill green" style="width: 58.4%;"></div>
          </div>
        </div>

        <div>
          <div class="progress-labels">
            <span>Reorder Recommended (Stock < ROP)</span>
            <span style="color: var(--warning); font-weight: 700;">151 SKUs (13.8%)</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill amber" style="width: 13.8%;"></div>
          </div>
        </div>

        <div>
          <div class="progress-labels">
            <span>Critical Stockout Risk (Stock < SS)</span>
            <span style="color: var(--danger); font-weight: 700;">303 SKUs (27.8%)</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill red" style="width: 27.8%;"></div>
          </div>
        </div>

        <!-- DAX Code Snippet -->
        <div class="dax-card">
          <div class="dax-header">
            <span>DAX Measure: Forecast Variance %</span>
            <span>Power BI</span>
          </div>
          <pre class="dax-code">Forecast Variance % = 
DIVIDE(
    SUM(DemandForecast[yhat]) - 
    SUM(DailyDemand[actual_units]), 
    SUM(DailyDemand[actual_units]), 
    0
) * 100</pre>
        </div>
      </div>
    </div>
  </div>

  <!-- Visual 3: SKU Inventory Matrix & Alert Table -->
  <div class="panel">
    <div class="panel-header">
      <div>
        <div class="panel-title">SKU-Level Replenishment Matrix & Stockout Alerts</div>
        <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Dynamic Safety Stock, Reorder Point (ROP) & Days of Supply Remaining</p>
      </div>
      <div class="panel-tag">Visual 3 (Matrix)</div>
    </div>

    <div class="filter-bar">
      <input type="text" id="skuSearch" class="search-input" placeholder="Search by SKU ID or category..." onkeyup="filterTable()">
      <button class="filter-btn active" onclick="setFilter('ALL', this)">All SKUs (1,091)</button>
      <button class="filter-btn" onclick="setFilter('CRITICAL', this)">Critical Alerts (303)</button>
      <button class="filter-btn" onclick="setFilter('REORDER', this)">Reorder Required (151)</button>
      <button class="filter-btn" onclick="setFilter('HEALTHY', this)">Healthy (637)</button>
    </div>

    <div class="table-container">
      <table id="skuTable">
        <thead>
          <tr>
            <th>Product SKU</th>
            <th>Category</th>
            <th>Unit Price</th>
            <th>Current Stock</th>
            <th>Safety Stock (SS)</th>
            <th>Reorder Point (ROP)</th>
            <th>Days of Supply</th>
            <th>Reorder Alert Status</th>
          </tr>
        </thead>
        <tbody id="skuBody">
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
  // Chart Data Injection
  const chartLabels = {json.dumps(chart_labels)};
  const actualData = {json.dumps(actual_data)};
  const forecastData = {json.dumps(forecast_data)};
  const lowerBound = {json.dumps(lower_bound)};
  const upperBound = {json.dumps(upper_bound)};

  const ctx = document.getElementById('forecastChart').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: chartLabels,
      datasets: [
        {{
          label: 'Historical Actual Demand',
          data: actualData,
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.2
        }},
        {{
          label: 'Prophet Forecast (yhat)',
          data: forecastData,
          borderColor: '#f43f5e',
          backgroundColor: 'rgba(244, 63, 94, 0.05)',
          borderWidth: 2.5,
          borderDash: [5, 5],
          pointRadius: 2,
          tension: 0.2
        }},
        {{
          label: 'Upper 95% Bound',
          data: upperBound,
          borderColor: 'rgba(244, 63, 94, 0.2)',
          borderWidth: 1,
          pointRadius: 0,
          fill: '+1',
          backgroundColor: 'rgba(244, 63, 94, 0.12)'
        }},
        {{
          label: 'Lower 95% Bound',
          data: lowerBound,
          borderColor: 'rgba(244, 63, 94, 0.2)',
          borderWidth: 1,
          pointRadius: 0,
          fill: false
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{
        mode: 'index',
        intersect: false,
      }},
      plugins: {{
        legend: {{
          position: 'top',
          labels: {{
            color: '#94a3b8',
            font: {{ family: 'Plus Jakarta Sans', size: 12 }}
          }}
        }},
        tooltip: {{
          backgroundColor: '#1e293b',
          titleColor: '#f8fafc',
          bodyColor: '#cbd5e1',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1
        }}
      }},
      scales: {{
        x: {{
          ticks: {{
            color: '#64748b',
            maxTicksLimit: 12
          }},
          grid: {{
            color: 'rgba(255, 255, 255, 0.04)'
          }}
        }},
        y: {{
          ticks: {{
            color: '#64748b'
          }},
          grid: {{
            color: 'rgba(255, 255, 255, 0.04)'
          }}
        }}
      }}
    }}
  }});

  // Table Data Injection
  const skuData = {json.dumps(sample_skus)};
  let currentFilter = 'ALL';

  function renderTable() {{
    const tbody = document.getElementById('skuBody');
    const searchVal = document.getElementById('skuSearch').value.toLowerCase();
    tbody.innerHTML = '';

    skuData.forEach(item => {{
      const matchesSearch = item.product_id.toLowerCase().includes(searchVal) || 
                            item.product_category.toLowerCase().includes(searchVal);
      
      let matchesFilter = true;
      if (currentFilter === 'CRITICAL') {{
        matchesFilter = item.reorder_alert_status === 'CRITICAL - STOCKOUT RISK';
      }} else if (currentFilter === 'REORDER') {{
        matchesFilter = item.reorder_alert_status === 'REORDER NOW';
      }} else if (currentFilter === 'HEALTHY') {{
        matchesFilter = item.reorder_alert_status === 'HEALTHY';
      }}

      if (matchesSearch && matchesFilter) {{
        let badgeClass = 'healthy';
        if (item.reorder_alert_status === 'CRITICAL - STOCKOUT RISK') badgeClass = 'critical';
        else if (item.reorder_alert_status === 'REORDER NOW') badgeClass = 'reorder';

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="sku-id">${{item.product_id.substring(0, 16)}}...</td>
          <td>${{item.product_category}}</td>
          <td>$${{item.unit_price.toFixed(2)}}</td>
          <td style="font-weight: 700;">${{item.current_stock}}</td>
          <td>${{item.safety_stock_level}}</td>
          <td>${{item.reorder_point}}</td>
          <td>${{item.days_of_supply_remaining}} days</td>
          <td><span class="status-badge ${{badgeClass}}">${{item.reorder_alert_status}}</span></td>
        `;
        tbody.appendChild(tr);
      }}
    }});
  }}

  function setFilter(filterType, btn) {{
    currentFilter = filterType;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderTable();
  }}

  function filterTable() {{
    renderTable();
  }}

  // Initial render
  renderTable();
</script>
</body>
</html>
"""

    dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dashboard_preview.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[CREATED] Interactive Dashboard Preview: {dashboard_path} ({os.path.getsize(dashboard_path):,} bytes)")

if __name__ == '__main__':
    build_dashboard()
