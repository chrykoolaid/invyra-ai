from __future__ import annotations
import os
import hashlib
import json
from typing import Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from . import storage
from .logic import daily_metrics, delta, explain

APP_VERSION = "sprint-A8-env-context-pack-01"
SCHEMA_VERSION = "1.0"

def _expected_key() -> str:
    return os.getenv("INVYRA_AI_INGEST_API_KEY","").strip()

def _mask_key(k: str) -> str:
    if not k:
        return ""
    if len(k) <= 4:
        return "*" * len(k)
    return "*"*(len(k)-4) + k[-4:]

def require_review_auth(x_api_key: Optional[str]) -> str:
    expected = _expected_key()
    if not expected:
        raise HTTPException(status_code=500, detail={
            "error":"misconfigured",
            "reason":"missing_env_key",
            "message":"Server misconfigured: INVYRA_AI_INGEST_API_KEY not set.",
            "hint":"Set INVYRA_AI_INGEST_API_KEY or use the start script."
        })
    if (x_api_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail={
            "error":"unauthorized",
            "reason":"missing_or_invalid_api_key",
            "message":"Unauthorized (API key). Enter X-API-Key or restart using the provided start script.",
            "hint": f"Expected key ending with {_mask_key(expected)[-4:]}"
        })
    return expected

DECISION_MODE = "review-only"  # immutable

def ai_enabled() -> bool:
    ks = os.getenv("INVYRA_AI_KILLSWITCH","1").strip().lower()
    return ks not in ("1","true","yes","on")

def ai_reason() -> str:
    return "AI enabled explicitly by operator." if ai_enabled() else "AI disabled by kill switch (default)."


def compute_bundle_id(workspace_id: str, day: str, compare_to: str, engine_version: str, schema_version: str) -> str:
    """Deterministic ID for audit correlation (does not hash the bundle itself)."""
    raw = f"{workspace_id}|{day}|{compare_to}|{engine_version}|{schema_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_manifest_text(bundle: dict) -> str:
    meta = bundle.get("meta", {})
    lines = [
        "INVYRA_AI_REVIEW_MANIFEST v1",
        f"bundle_id: {meta.get('bundle_id','')}",
        f"engine_version: {meta.get('engine_version','')}",
        f"schema_version: {meta.get('schema_version','')}",
        f"workspace_id: {meta.get('workspace_id','')}",
        f"day: {meta.get('day','')}",
        f"compare_to: {meta.get('compare_to','')}",
        f"generated_at: {meta.get('generated_at','')}",
        f"audit_safe: {bundle.get('ai_status',{}).get('audit_safe', True)}",
    ]

    # A8: environment context (if present)
    ctx = meta.get("env_context") or {}
    if ctx:
        lines.append("")
        lines.append("[ENV_CONTEXT]")
        for key in ("invyra_env", "role", "terminal", "user_id", "timezone_offset", "locale", "os", "python", "arch", "hostname_hash", "generated_at_utc"):
            lines.append(f"{key}={ctx.get(key, 'unknown')}")

    return "\n".join(lines) + "\n"


app = FastAPI(title="Invyra AI Engine", version=APP_VERSION)

@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={
        "error":"http_error",
        "reason":"unknown",
        "message": str(detail),
    })

class EventIn(BaseModel):
    event_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    ts_utc: str = Field(..., min_length=10)
    amount: Optional[float] = None

class IngestReq(BaseModel):
    workspace_id: str = Field(..., min_length=1)
    events: list[EventIn]

@app.get("/health")
def health():
    return {"status":"ok","engine_version":APP_VERSION,"schema_version":SCHEMA_VERSION,"time_utc":datetime.now(timezone.utc).isoformat()}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/ai/status")
def status(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    enabled = ai_enabled()
    return {
        "status":"ok",
        "ai_enabled": enabled,
        "reason": ai_reason(),
        "level": "info" if enabled else "warning",
        "decision_mode": DECISION_MODE,
        "allowed_actions": [],
        "audit_safe": True,
        "engine_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "provider": {"provider":"none","mode":DECISION_MODE,"notes":"Deterministic; no actions."}
    }

@app.post("/actions/apply")
def actions_apply(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    raise HTTPException(status_code=403, detail={
        "error":"actions_disabled",
        "message":"Actions are disabled in review-only engine"
    })

@app.post("/ingest/events")
def ingest(req: IngestReq, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    existing = {e.get("event_id") for e in storage.list_events(req.workspace_id)}
    accepted = []
    results = []
    for e in req.events:
        if e.event_id in existing:
            results.append({"event_id":e.event_id,"status":"duplicate"})
        else:
            accepted.append(e.model_dump())
            existing.add(e.event_id)
            results.append({"event_id":e.event_id,"status":"accepted"})
    if accepted:
        storage.append_events(req.workspace_id, accepted)
    return {"accepted": sum(1 for r in results if r["status"]=="accepted"), "duplicates": sum(1 for r in results if r["status"]=="duplicate"), "results": results}

@app.get("/patterns/day")
def patterns_day(workspace_id: str, day: str, compare_to: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    ev = storage.list_events(workspace_id)
    a = daily_metrics(ev, day)
    b = daily_metrics(ev, compare_to)
    payload = {"workspace_id":workspace_id,"day":day,"compare_to":compare_to,"day_metrics":a,"compare_metrics":b,"delta":delta(a,b),
               "notes":"Deterministic output. Human must review; no actions applied."}
    print(f"[REVIEW] patterns ws={workspace_id} day={day} compare={compare_to} auth=ok")
    return payload

@app.get("/explain/day")
def explain_day(workspace_id: str, day: str, compare_to: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    patterns = patterns_day(workspace_id, day, compare_to, x_api_key=x_api_key)
    e = explain(patterns, ai_enabled())
    e["generated_at"] = datetime.now(timezone.utc).isoformat()
    return e

@app.get("/review/bundle")
def review_bundle(workspace_id: str, day: str, compare_to: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    s = status(x_api_key=x_api_key)
    p = patterns_day(workspace_id, day, compare_to, x_api_key=x_api_key)
    ex = explain(p, ai_enabled())
    ex["generated_at"] = datetime.now(timezone.utc).isoformat()
    generated_at = datetime.now(timezone.utc).isoformat()
    bundle_id = compute_bundle_id(workspace_id, day, compare_to, APP_VERSION, SCHEMA_VERSION)
    print(f"[REVIEW] bundle ws={workspace_id} day={day} compare={compare_to} auth=ok")
    bundle = {
        "meta": {
            "engine_version": APP_VERSION,
            "schema_version": SCHEMA_VERSION,
            "source": "bundle",
            "bundle_id": bundle_id,
            "workspace_id": workspace_id,
            "day": day,
            "compare_to": compare_to,
            "generated_at": generated_at,
        },
        "ai_status": s,
        "deterministic_patterns": p,
        "ai_explanation": ex,
    }
    return bundle

@app.get("/review/manifest")
def review_manifest(workspace_id: str, day: str, compare_to: str, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    require_review_auth(x_api_key)
    bundle = review_bundle(workspace_id, day, compare_to, x_api_key=x_api_key)
    manifest = make_manifest_text(bundle)
    return Response(content=manifest, media_type="text/plain; charset=utf-8")

UI_HTML = r'''<!doctype html><html><head><meta charset="utf-8"><title>Invyra AI Review</title>
<style>
body{font-family:system-ui,Segoe UI,Arial;margin:24px;max-width:1150px}
.row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
input,button{padding:10px;font-size:14px}input{min-width:240px}
.card{border:1px solid #ddd;border-radius:12px;padding:14px;margin-top:14px}
pre{background:#fafafa;border:1px solid #eee;padding:12px;border-radius:12px;overflow:auto}
button{cursor:pointer}.primary{font-weight:600}.muted{color:#666}
.badge{display:inline-block;padding:2px 8px;border:1px solid #999;border-radius:999px;font-size:12px;margin-left:8px}
#errorBanner{padding:10px;border:1px solid #c77;border-radius:12px;background:#fff6f6}
</style></head><body>
<h1>AI Explanation Review Panel <span class="badge">READ-ONLY</span></h1>
<p class="muted">Bundle-first flow. Humans remain in control. No actions are applied.</p>
<p class="muted"><strong>Build:</strong> sprint-A8-env-context-pack-01</p>

<div id="errorBanner" role="alert" aria-live="polite" tabindex="-1" hidden></div>

<div class="card">
  <div class="row">
    <input id="apiKey" placeholder="X-API-Key (e.g. test_key_123)">
    <input id="ws" value="ws_test_001">
    <input id="day" value="2026-01-30">
    <input id="compare" value="2026-01-29">
    <button onclick="resetKey()">Reset API key</button>
  </div>

  <div class="row">
    <button class="primary" onclick="loadBundle()">Load review bundle (recommended)</button>
    <span id="bundleState" class="badge" hidden>Bundle loaded ✓</span>
  </div>

  <div class="row">
    <button id="btnDownload" onclick="downloadBundle()" disabled>Download Bundle JSON</button>
    <button id="btnCopy" onclick="copyBundle()" disabled>Copy Bundle JSON</button>
    <button id="btnManifest" onclick="downloadManifest()" disabled>Download Manifest</button>
    <button id="btnCopyId" onclick="copyBundleId()" disabled>Copy Bundle ID</button>
    <span class="muted" id="exportHint">Load the bundle to enable export.</span>
  </div>

  <div class="row">
    <label class="muted"><input type="checkbox" id="advancedToggle" onchange="toggleAdvanced()"> Advanced</label>
    <span class="muted">Advanced enables legacy calls; bundle is recommended for consistency.</span>
  </div>

  <div class="row" id="advancedRow" style="opacity:0.6">
    <button id="btnStatus" onclick="checkStatus()">Check AI status</button>
    <button id="btnPatterns" onclick="loadPatterns()">Load deterministic patterns</button>
    <button id="btnExplain" onclick="loadExplain()">Load deterministic explanation</button>
  </div>
</div>

<div class="card"><h3>Status</h3><pre id="outStatus">Not loaded. Use “Load review bundle”.</pre></div>
<div class="card"><h3>Deterministic patterns (authoritative)</h3><pre id="outPatterns">Not loaded. Use “Load review bundle”.</pre></div>
<div class="card"><h3>AI explanation (advisory)</h3><pre id="outExplain">Not loaded. Use “Load review bundle”.</pre></div>

<script>
const LS_KEY="invyra_api_key";
function showError(msg){
  const el=document.getElementById("errorBanner");
  el.textContent=msg; el.hidden=false;
  el.scrollIntoView({behavior:"smooth",block:"start"});
  el.focus({preventScroll:true});
}
function clearError(){const el=document.getElementById("errorBanner"); el.hidden=true; el.textContent="";}
function setBundleLoaded(v){document.getElementById("bundleState").hidden=!v;}
let lastBundleText = null;
function setExportEnabled(on){
  document.getElementById("btnDownload").disabled=!on;
  document.getElementById("btnCopy").disabled=!on;
  document.getElementById("btnManifest").disabled=!on;
  document.getElementById("btnCopyId").disabled=!on;
  document.getElementById("exportHint").textContent = on ? "Export ready." : "Load the bundle to enable export.";
}

function toggleAdvanced(){
  const on=document.getElementById("advancedToggle").checked;
  const row=document.getElementById("advancedRow");
  row.style.opacity=on?"1.0":"0.6";
  document.getElementById("btnStatus").disabled=!on;
  document.getElementById("btnPatterns").disabled=!on;
  document.getElementById("btnExplain").disabled=!on;
  if(!on) setBundleLoaded(false);
  setExportEnabled(false);
}
function resetKey(){
  localStorage.removeItem(LS_KEY);
  document.getElementById("apiKey").value="";
  showError("API key cleared. Enter your X-API-Key, then load the review bundle.");
  setBundleLoaded(false);
  setExportEnabled(false);
}
function getKey(){
  const k=(document.getElementById("apiKey").value||"").trim();
  if(!k){showError("Unauthorized (API key). Enter X-API-Key or restart using the provided start script."); throw new Error("missing_api_key");}
  localStorage.setItem(LS_KEY,k);
  return k;
}
async function callApi(path){
  clearError();
  const apiKey=getKey();
  const res=await fetch(path,{headers:{"X-API-Key":apiKey}});
  const txt=await res.text();
  let obj=null; try{obj=JSON.parse(txt);}catch{}
  if(!res.ok){
    const msg=(obj && (obj.message||obj.error)) ? (obj.message||obj.error) : `Request failed (${res.status}).`;
    const hint=(obj && obj.hint) ? (" "+obj.hint) : "";
    showError(msg+hint);
    return {ok:false,obj,raw:txt};
  }
  return {ok:true,obj,raw:txt};
}
async function checkStatus(){
  setBundleLoaded(false);
  setExportEnabled(false);
  const r=await callApi("/ai/status");
  document.getElementById("outStatus").textContent=r.obj?JSON.stringify(r.obj,null,2):r.raw;
}
async function loadPatterns(){
  setBundleLoaded(false);
  setExportEnabled(false);
  const ws=document.getElementById("ws").value, day=document.getElementById("day").value, compare=document.getElementById("compare").value;
  const url=`/patterns/day?workspace_id=${encodeURIComponent(ws)}&day=${encodeURIComponent(day)}&compare_to=${encodeURIComponent(compare)}`;
  const r=await callApi(url);
  document.getElementById("outPatterns").textContent=r.obj?JSON.stringify(r.obj,null,2):r.raw;
}
async function loadExplain(){
  setBundleLoaded(false);
  setExportEnabled(false);
  const ws=document.getElementById("ws").value, day=document.getElementById("day").value, compare=document.getElementById("compare").value;
  const url=`/explain/day?workspace_id=${encodeURIComponent(ws)}&day=${encodeURIComponent(day)}&compare_to=${encodeURIComponent(compare)}`;
  const r=await callApi(url);
  document.getElementById("outExplain").textContent=r.obj?JSON.stringify(r.obj,null,2):r.raw;
}

async function downloadBundle(){
  if(!lastBundleText){showError("No bundle loaded yet."); return;}
  const ws=document.getElementById("ws").value||"ws";
  const day=document.getElementById("day").value||"day";
  const compare=document.getElementById("compare").value||"compare";
  const filename=`invyra_review_bundle_${ws}_${day}_vs_${compare}.json`;
  const blob=new Blob([lastBundleText],{type:"application/json"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url; a.download=filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
async function copyBundle(){
  if(!lastBundleText){showError("No bundle loaded yet."); return;}
  try{
    await navigator.clipboard.writeText(lastBundleText);
  }catch(e){
    const ta=document.createElement("textarea");
    ta.value=lastBundleText;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

async function copyBundleId(){
  if(!lastBundleText){showError("No bundle loaded yet."); return;}
  try{
    const obj=JSON.parse(lastBundleText);
    const id=(obj.meta&&obj.meta.bundle_id)||"";
    if(!id){showError("Bundle ID not present."); return;}
    await navigator.clipboard.writeText(id);
  }catch(e){showError("Failed to copy bundle ID.");}
}

async function downloadManifest(){
  const ws=document.getElementById("ws").value, day=document.getElementById("day").value, compare=document.getElementById("compare").value;
  const url=`/review/manifest?workspace_id=${encodeURIComponent(ws)}&day=${encodeURIComponent(day)}&compare_to=${encodeURIComponent(compare)}`;
  const r=await callApi(url);
  if(!r.ok) return;
  let filename=`invyra_review_manifest_${ws}_${day}_vs_${compare}.txt`;
  try{
    if(lastBundleText){
      const obj=JSON.parse(lastBundleText);
      const id=(obj.meta&&obj.meta.bundle_id)||"";
      if(id) filename=`invyra_review_manifest_${id}.txt`;
    }
  }catch(e){}
  const blob=new Blob([r.raw],{type:"text/plain"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob);
  a.download=filename;
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href), 1000);
}

async function loadBundle(){
  const ws=document.getElementById("ws").value, day=document.getElementById("day").value, compare=document.getElementById("compare").value;
  const url=`/review/bundle?workspace_id=${encodeURIComponent(ws)}&day=${encodeURIComponent(day)}&compare_to=${encodeURIComponent(compare)}`;
  const r=await callApi(url);
  if(!r.ok) return;
  lastBundleText = r.raw;
  setBundleLoaded(true);
  setExportEnabled(true);
  const obj=r.obj||{};
  document.getElementById("outStatus").textContent=obj.ai_status?JSON.stringify(obj.ai_status,null,2):"No status returned.";
  document.getElementById("outPatterns").textContent=obj.deterministic_patterns?JSON.stringify(obj.deterministic_patterns,null,2):"No patterns returned.";
  document.getElementById("outExplain").textContent=obj.ai_explanation?JSON.stringify(obj.ai_explanation,null,2):"No explanation returned.";
}
(function init(){
  const saved=localStorage.getItem(LS_KEY);
  if(saved) document.getElementById("apiKey").value=saved;
  toggleAdvanced();
  setExportEnabled(false);
})();
</script></body></html>'''

@app.get("/ui/ai-review", response_class=HTMLResponse)
def ui():
    return HTMLResponse(UI_HTML)
