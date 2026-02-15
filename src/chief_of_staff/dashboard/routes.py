"""Dashboard API routes and HTML frontend."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from chief_of_staff.agent.activity import (
    get_recent_activity, get_activity_stats, get_agent_activity_summary,
)
from chief_of_staff.agent.registry import get_registry

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/api/activity")
async def api_activity(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    agent: str | None = Query(None),
    action_type: str | None = Query(None),
    hours: int | None = Query(None),
):
    """Get recent activity feed."""
    return get_recent_activity(
        limit=limit,
        offset=offset,
        agent_name=agent,
        action_type=action_type,
        since_hours=hours,
    )


@router.get("/api/stats")
async def api_stats(hours: int = Query(24)):
    """Get aggregate activity stats."""
    return get_activity_stats(hours=hours)


@router.get("/api/agents")
async def api_agents():
    """Get all agents and their activity summaries."""
    registry = get_registry()
    agents = registry.list_agents()
    activity = get_agent_activity_summary()
    activity_map = {a["agent_name"]: a for a in activity}

    result = []
    for agent in agents:
        a_data = activity_map.get(agent.name, {})
        result.append({
            "name": agent.name,
            "display_name": agent.display_name,
            "model": agent.model,
            "tools": agent.tools,
            "standing_instructions": agent.standing_instructions,
            "permissions": agent.permissions,
            "total_actions": a_data.get("total_actions", 0),
            "last_active": a_data.get("last_active", "never"),
            "messages": a_data.get("messages", 0),
            "tool_uses": a_data.get("tool_uses", 0),
        })
    return result


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the dashboard HTML."""
    return DASHBOARD_HTML


# ---------------------------------------------------------------------------
# Dashboard HTML (single-page app with embedded CSS + JS)
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arcuate Agent Dashboard</title>
<style>
  :root {
    --bg: #0c0e14;
    --surface: #151821;
    --surface2: #1c2030;
    --border: #2a2e3f;
    --text: #e2e8f0;
    --text-dim: #8892a8;
    --accent: #6366f1;
    --accent-dim: #4f46e5;
    --green: #22c55e;
    --yellow: #f59e0b;
    --red: #ef4444;
    --blue: #3b82f6;
    --purple: #a855f7;
    --pink: #ec4899;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; font-size: 13px; }

  .header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header h1 { font-size: 16px; font-weight: 600; letter-spacing: 0.5px; }
  .header h1 span { color: var(--accent); }
  .header-right { display: flex; align-items: center; gap: 16px; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); display: inline-block; animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .auto-refresh { color: var(--text-dim); font-size: 11px; }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    padding: 16px 24px;
  }
  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
  }
  .stat-card .label { color: var(--text-dim); font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  .stat-card .value { font-size: 24px; font-weight: 700; }
  .stat-card .sub { color: var(--text-dim); font-size: 10px; margin-top: 2px; }
  .stat-card.messages .value { color: var(--blue); }
  .stat-card.tools .value { color: var(--purple); }
  .stat-card.searches .value { color: var(--yellow); }
  .stat-card.agents .value { color: var(--green); }
  .stat-card.configs .value { color: var(--pink); }
  .stat-card.errors .value { color: var(--red); }

  .content { display: grid; grid-template-columns: 1fr 300px; gap: 0; min-height: calc(100vh - 200px); }

  .feed-section { border-right: 1px solid var(--border); }
  .section-header {
    padding: 12px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--surface);
  }
  .section-header h2 { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim); }
  .filters { display: flex; gap: 8px; }
  .filters select {
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
    font-family: inherit;
    cursor: pointer;
  }

  .feed { overflow-y: auto; max-height: calc(100vh - 260px); }
  .feed-item {
    display: grid;
    grid-template-columns: 80px 120px 130px 1fr;
    gap: 12px;
    padding: 10px 24px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    transition: background 0.15s;
  }
  .feed-item:hover { background: var(--surface); }
  .feed-item.new { animation: fadeIn 0.3s ease-in; }
  @keyframes fadeIn { from { opacity: 0; background: var(--accent-dim); } to { opacity: 1; } }
  .feed-time { color: var(--text-dim); }
  .feed-agent { color: var(--accent); font-weight: 500; }
  .feed-action { font-weight: 500; }
  .feed-detail { color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .action-badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .action-badge.message_received { background: #1e3a5f; color: #60a5fa; }
  .action-badge.message_sent { background: #1a3c2a; color: #4ade80; }
  .action-badge.tool_use { background: #2d1f54; color: #c084fc; }
  .action-badge.knowledge_search { background: #3d2f0a; color: #fbbf24; }
  .action-badge.web_search { background: #0c3547; color: #38bdf8; }
  .action-badge.config_update { background: #3b1d42; color: #f0abfc; }
  .action-badge.memory_write { background: #1a3333; color: #5eead4; }
  .action-badge.memory_read { background: #1a3333; color: #5eead4; }
  .action-badge.sub_agent_spawn { background: #1f3d1f; color: #86efac; }
  .action-badge.delegation { background: #2a2040; color: #a78bfa; }
  .action-badge.error { background: #3b1515; color: #fca5a5; }
  .action-badge.sms_received { background: #1e3a5f; color: #60a5fa; }
  .action-badge.sms_sent { background: #1a3c2a; color: #4ade80; }
  .action-badge.call_ingested { background: #2d1f54; color: #c084fc; }
  .action-badge.email_ingested { background: #3d2f0a; color: #fbbf24; }
  .action-badge.doc_ingested { background: #3d2f0a; color: #fbbf24; }
  .action-badge.meeting_ingested { background: #1f3d1f; color: #86efac; }
  .action-badge.ingestion_sync { background: #1a2633; color: #7dd3fc; }
  .action-badge.webhook_received { background: #1a2633; color: #7dd3fc; }

  .sidebar { background: var(--surface); overflow-y: auto; }
  .agent-card {
    padding: 16px;
    border-bottom: 1px solid var(--border);
  }
  .agent-card h3 { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
  .agent-card .agent-meta { font-size: 11px; color: var(--text-dim); margin-bottom: 4px; }
  .agent-card .agent-stat { font-size: 11px; margin-bottom: 2px; }
  .agent-card .agent-stat span { color: var(--accent); font-weight: 600; }
  .instructions-list { margin-top: 8px; padding-left: 16px; }
  .instructions-list li { font-size: 10px; color: var(--text-dim); margin-bottom: 4px; line-height: 1.4; }

  .empty-state { padding: 40px 24px; text-align: center; color: var(--text-dim); }
  .empty-state p { font-size: 13px; margin-bottom: 8px; }

  @media (max-width: 768px) {
    .content { grid-template-columns: 1fr; }
    .feed-item { grid-template-columns: 70px 100px 1fr; }
    .feed-detail { display: none; }
  }
</style>
</head>
<body>

<div class="header">
  <h1><span>ARCUATE</span> Agent Dashboard</h1>
  <div class="header-right">
    <span class="status-dot"></span>
    <span class="auto-refresh">Auto-refresh: <span id="countdown">5</span>s</span>
    <span class="auto-refresh" id="last-updated"></span>
  </div>
</div>

<div class="stats-row" id="stats-row"></div>

<div class="content">
  <div class="feed-section">
    <div class="section-header">
      <h2>Activity Feed</h2>
      <div class="filters">
        <select id="filter-agent" onchange="refresh()">
          <option value="">All Agents</option>
        </select>
        <select id="filter-action" onchange="refresh()">
          <option value="">All Actions</option>
          <option value="message_received">Messages In</option>
          <option value="message_sent">Messages Out</option>
          <option value="tool_use">Tool Use</option>
          <option value="knowledge_search">KB Search</option>
          <option value="web_search">Web Search</option>
          <option value="config_update">Config Update</option>
          <option value="memory_write">Memory Write</option>
          <option value="sub_agent_spawn">Agent Spawn</option>
          <option value="delegation">Delegation</option>
          <option value="sms_received">SMS In</option>
          <option value="sms_sent">SMS Out</option>
          <option value="call_ingested">Call Transcript</option>
          <option value="email_ingested">Email Ingested</option>
          <option value="doc_ingested">Doc Ingested</option>
          <option value="meeting_ingested">Meeting Ingested</option>
          <option value="ingestion_sync">Sync Cycle</option>
          <option value="webhook_received">Webhook</option>
          <option value="error">Error</option>
        </select>
        <select id="filter-hours" onchange="refresh()">
          <option value="1">Last Hour</option>
          <option value="24" selected>Last 24h</option>
          <option value="168">Last 7d</option>
          <option value="">All Time</option>
        </select>
      </div>
    </div>
    <div class="feed" id="feed"></div>
  </div>

  <div class="sidebar">
    <div class="section-header"><h2>Agents</h2></div>
    <div id="agents-list"></div>
  </div>
</div>

<script>
const BASE = '/dashboard/api';
let lastActivityId = null;

function formatTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso + 'Z');
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(iso) {
  if (!iso || iso === 'never') return 'never';
  const d = new Date(iso + 'Z');
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function truncate(s, max) {
  if (!s) return '';
  return s.length > max ? s.slice(0, max) + '...' : s;
}

async function fetchJSON(url) {
  const resp = await fetch(url);
  return resp.json();
}

async function loadStats() {
  const hours = document.getElementById('filter-hours').value || '';
  const params = hours ? `?hours=${hours}` : '?hours=8760';
  const stats = await fetchJSON(BASE + '/stats' + params);
  const row = document.getElementById('stats-row');
  const totalMsgs = stats.messages_received + stats.messages_sent + stats.sms_received + stats.sms_sent;
  const totalIngested = stats.emails_ingested + stats.calls_ingested + stats.docs_ingested + stats.meetings_ingested;
  row.innerHTML = `
    <div class="stat-card messages">
      <div class="label">Messages</div>
      <div class="value">${totalMsgs}</div>
      <div class="sub">Discord: ${stats.messages_received}in/${stats.messages_sent}out &middot; SMS: ${stats.sms_received}in/${stats.sms_sent}out</div>
    </div>
    <div class="stat-card tools">
      <div class="label">Tool Uses</div>
      <div class="value">${stats.tool_uses}</div>
      <div class="sub">${stats.knowledge_searches} KB &middot; ${stats.web_searches} web &middot; ${stats.delegations} delegated</div>
    </div>
    <div class="stat-card searches">
      <div class="label">Ingested</div>
      <div class="value">${totalIngested}</div>
      <div class="sub">${stats.emails_ingested} emails &middot; ${stats.calls_ingested} calls &middot; ${stats.docs_ingested} docs &middot; ${stats.meetings_ingested} meetings</div>
    </div>
    <div class="stat-card agents">
      <div class="label">Agents</div>
      <div class="value">${stats.active_agents.length}</div>
      <div class="sub">${stats.sub_agents_spawned} spawned &middot; ${stats.sync_cycles} syncs</div>
    </div>
    <div class="stat-card configs">
      <div class="label">Self-Mod</div>
      <div class="value">${stats.config_updates + stats.memory_writes}</div>
      <div class="sub">${stats.config_updates} config &middot; ${stats.memory_writes} memories</div>
    </div>
    <div class="stat-card errors">
      <div class="label">Errors</div>
      <div class="value">${stats.errors}</div>
      <div class="sub">${stats.all_time_total} all-time actions</div>
    </div>
  `;
}

async function loadFeed() {
  const agent = document.getElementById('filter-agent').value;
  const action = document.getElementById('filter-action').value;
  const hours = document.getElementById('filter-hours').value;
  let url = BASE + '/activity?limit=100';
  if (agent) url += '&agent=' + agent;
  if (action) url += '&action_type=' + action;
  if (hours) url += '&hours=' + hours;

  const items = await fetchJSON(url);
  const feed = document.getElementById('feed');

  if (items.length === 0) {
    feed.innerHTML = '<div class="empty-state"><p>No activity yet</p><p>Send a message to the bot to get started</p></div>';
    return;
  }

  const newFirstId = items[0]?.id;
  const isNew = lastActivityId && newFirstId !== lastActivityId;

  feed.innerHTML = items.map((item, i) => `
    <div class="feed-item ${isNew && i === 0 ? 'new' : ''}">
      <div class="feed-time">${formatTime(item.timestamp)}</div>
      <div class="feed-agent">${item.agent_name}</div>
      <div class="feed-action"><span class="action-badge ${item.action_type}">${item.action_type.replace(/_/g, ' ')}</span></div>
      <div class="feed-detail" title="${(item.action_detail || item.input_summary || '').replace(/"/g, '&quot;')}">${truncate(item.action_detail || item.input_summary || '', 80)}</div>
    </div>
  `).join('');

  lastActivityId = newFirstId;
}

async function loadAgents() {
  const agents = await fetchJSON(BASE + '/agents');
  const list = document.getElementById('agents-list');
  const select = document.getElementById('filter-agent');

  // Update filter dropdown
  const currentFilter = select.value;
  select.innerHTML = '<option value="">All Agents</option>' + agents.map(a => `<option value="${a.name}">${a.display_name}</option>`).join('');
  select.value = currentFilter;

  if (agents.length === 0) {
    list.innerHTML = '<div class="empty-state"><p>No agents configured</p></div>';
    return;
  }

  list.innerHTML = agents.map(a => `
    <div class="agent-card">
      <h3>${a.display_name}</h3>
      <div class="agent-meta">${a.name} &middot; ${a.model}</div>
      <div class="agent-stat">Actions: <span>${a.total_actions}</span></div>
      <div class="agent-stat">Messages: <span>${a.messages}</span></div>
      <div class="agent-stat">Tool uses: <span>${a.tool_uses}</span></div>
      <div class="agent-stat">Last active: ${formatDate(a.last_active)}</div>
      <div class="agent-meta" style="margin-top:8px">Tools: ${a.tools.join(', ')}</div>
      ${a.standing_instructions.length > 0 ? `
        <div class="agent-meta" style="margin-top:6px">Standing instructions:</div>
        <ol class="instructions-list">
          ${a.standing_instructions.map(inst => `<li>${inst}</li>`).join('')}
        </ol>
      ` : ''}
    </div>
  `).join('');
}

async function refresh() {
  try {
    await Promise.all([loadStats(), loadFeed(), loadAgents()]);
    document.getElementById('last-updated').textContent = 'Updated: ' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error('Refresh failed:', e);
  }
}

// Auto-refresh countdown
let countdown = 5;
setInterval(() => {
  countdown--;
  document.getElementById('countdown').textContent = countdown;
  if (countdown <= 0) {
    countdown = 5;
    refresh();
  }
}, 1000);

// Initial load
refresh();
</script>
</body>
</html>"""
