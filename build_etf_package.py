from __future__ import annotations

import hashlib
import shutil
import textwrap
import zipfile
from pathlib import Path

ROOT = Path("korea_etf_selective_compliance")
ZIP = Path("korea_etf_selective_compliance_complete.zip")

if ROOT.exists():
    shutil.rmtree(ROOT)
if ZIP.exists():
    ZIP.unlink()

for d in [
    "config", "docs", "src/etf_compliance", "scripts", "tests", "examples",
    "data/raw/kind", "data/raw/krx/closing_premium", "data/raw/krx/investor_buy",
    "data/raw/krx/investor_sell", "data/raw/krx/market_actions",
    "data/interim", "data/processed", "outputs/tables", "outputs/figures", "outputs/logs",
    "tools",
]:
    (ROOT / d).mkdir(parents=True, exist_ok=True)

F: dict[str, str] = {}

F["README.md"] = r'''
# Korean ETF Selective Compliance Research Pipeline

A reproducible package for studying objectively triggered ETF disclosures,
selective compliance, enforcement, automation, capacity constraints, and market
consequences.

## Scientific guardrails

The code blocks unsupported claims by design:

- no `mandatory` or `noncompliance` label until the applicable official rule is
  verified in `config/legal_rules.csv`;
- documents, product-day events, continuous episodes, and exchange actions are
  distinct observation units;
- collection failure is never coded as silence;
- an outcome-derived treatment type is prohibited;
- causal estimates require an externally documented enforcement, automation,
  vendor, outage, or queue shock;
- estimator choice is fixed before outcomes are examined.

## Demo

```bash
python scripts/make_demo_data.py
python scripts/run_all.py --config config/demo.yaml
pytest -q
```

## Real-data workflow

1. Place KIND disclosure tables in `data/raw/kind/`.
2. Place official KRX closing price/NAV files in
   `data/raw/krx/closing_premium/`.
3. Place official investor files in `investor_buy/` and `investor_sell/`.
4. Complete and source-lock `config/legal_rules.csv`.
5. Add only externally validated compliance shocks to
   `config/compliance_shocks.csv`.
6. Run `python scripts/run_all.py --config config/project.yaml`.

## Main outputs

- `eligibility_risk_set.parquet`
- `required_filings.parquet`
- `issuer_compliance_summary.csv`
- `selection_function.csv`
- `first_stage.csv`
- `causal_estimates.csv`
- `GO_NO_GO.md`

## Top-journal gate

A JFE/RFS package requires a verified objective trigger, robust unexplained
nonfiling, large issuer dispersion, an externally validated compliance shock,
a strong first stage, credible exclusion restrictions, market consequences,
and a mechanism. A Management Science package additionally requires a verified
operational automation/capacity mechanism and an implementable counterfactual.
'''

F["LICENSE"] = '''MIT License\n\nCopyright (c) 2026\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\nof this software to deal in the Software without restriction. Third-party\nsource data are not covered by this license.\n'''

F["CITATION.cff"] = '''cff-version: 1.2.0\ntitle: "Korean ETF Selective Compliance Research Pipeline"\nmessage: "Cite the software release and official underlying sources."\ntype: software\nversion: 0.1.0\ndate-released: 2026-07-19\nlicense: MIT\nauthors:\n  - family-names: "Research Team"\n    given-names: "ETF Compliance"\n'''

F["pyproject.toml"] = r'''
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "etf-selective-compliance"
version = "0.1.0"
description = "Selective-compliance and enforcement analysis for Korean ETFs"
requires-python = ">=3.10"
dependencies = [
  "pandas>=2.0", "numpy>=1.24", "scipy>=1.10", "statsmodels>=0.14",
  "pyyaml>=6.0", "pyarrow>=12", "openpyxl>=3.1", "matplotlib>=3.7"
]

[project.optional-dependencies]
dev = ["pytest>=7.4"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
'''

F["requirements.txt"] = '''pandas>=2.0\nnumpy>=1.24\nscipy>=1.10\nstatsmodels>=0.14\npyyaml>=6.0\npyarrow>=12\nopenpyxl>=3.1\nmatplotlib>=3.7\npytest>=7.4\n'''

F["Makefile"] = '''.PHONY: demo test run clean\n\ndemo:\n\tpython scripts/make_demo_data.py\n\tpython scripts/run_all.py --config config/demo.yaml\n\ntest:\n\tpytest -q\n\nrun:\n\tpython scripts/run_all.py --config config/project.yaml\n\nclean:\n\trm -rf data/interim/* data/processed/* outputs/tables/* outputs/figures/* outputs/logs/*\n'''

F["config/project.yaml"] = r'''
project_name: korean_etf_selective_compliance
demo_mode: false
random_seed: 20260719
paths:
  kind: data/raw/kind
  closing_premium: data/raw/krx/closing_premium
  investor_buy: data/raw/krx/investor_buy
  investor_sell: data/raw/krx/investor_sell
  market_actions: data/raw/krx/market_actions
  legal_rules: config/legal_rules.csv
  compliance_shocks: config/compliance_shocks.csv
  processed: data/processed
  outputs: outputs
analysis:
  episode_gap_business_days: 1
  compliance_survival_threshold: 0.70
  issuer_dispersion_min_pp: 20.0
  min_eligible_events: 300
  min_shock_first_stage_f: 15.0
  event_window_pre: 20
  event_window_post: 20
validation:
  accounting_tolerance_bp: 5.0
  min_product_day_coverage: 0.95
'''

F["config/demo.yaml"] = r'''
project_name: demo_selective_compliance
demo_mode: true
random_seed: 20260719
paths:
  kind: examples/demo_kind.csv
  closing_premium: examples/demo_product_day.csv
  investor_buy: examples/demo_investor_buy.csv
  investor_sell: examples/demo_investor_sell.csv
  market_actions: examples/demo_market_actions.csv
  legal_rules: examples/demo_legal_rules.csv
  compliance_shocks: examples/demo_shocks.csv
  processed: data/processed
  outputs: outputs
analysis:
  episode_gap_business_days: 1
  compliance_survival_threshold: 0.70
  issuer_dispersion_min_pp: 20.0
  min_eligible_events: 100
  min_shock_first_stage_f: 10.0
  event_window_pre: 10
  event_window_post: 10
validation:
  accounting_tolerance_bp: 5.0
  min_product_day_coverage: 0.90
'''

F["config/legal_rules.csv"] = '''rule_id,market_scope,product_type,threshold_abs,threshold_unit,effective_start,effective_end,filing_deadline_business_days,episode_rule,responsible_party,legal_status,verified,source_url,source_document,notes\nPLACEHOLDER_DOMESTIC,domestic,ETF,0.01,decimal,2024-01-01,,1,daily,issuer,UNVERIFIED,false,,,Replace after official audit\nPLACEHOLDER_FOREIGN,foreign,ETF,0.02,decimal,2024-01-01,,1,daily,issuer,UNVERIFIED,false,,,Replace after official audit\n'''

F["config/compliance_shocks.csv"] = '''shock_id,issuer_id,shock_type,announcement_date,effective_date,validated_external_source,source_url,expected_first_stage_direction,notes\n'''

F["docs/THEORY.md"] = r'''
# Theory: Objective Triggers and Selective Compliance

An objective trigger is crossed when severity \(x\) exceeds \(c\):

\[
E=\mathbf 1(x\ge c).
\]

An issuer observes latent event type \(\theta\), chooses filing \(a\in\{0,1\}\),
and faces filing cost

\[
C_\theta(x,z)=k+r_\theta(x)+f_\theta(x,z),
\]

and expected nonfiling cost

\[
N(x,e)=q(e,x)F+L(x).
\]

The optimal rule is

\[
a^*=\mathbf 1\{N\ge C_\theta\}.
\]

## Propositions

1. **Selective compliance.** If \(\min C_\theta<N<\max C_\theta\), then
   \(0<Pr(a=1\mid E=1)<1\).
2. **Issuer heterogeneity.** Compliance rises with detection and sanctions and
   falls with filing cost.
3. **Endogenous signal composition.** Filings may overrepresent either severe
   events or benign events, depending on relative filing costs; filing versus
   silence is therefore not causal.
4. **Enforcement–informativeness trade-off.** Enforcement can increase
   completeness while reducing the information content of the filing indicator.
5. **Automation.** Automation lowers fixed cost or raises capacity, increasing
   coverage but changing marginal-event composition.
6. **Capacity constraints.** An issuer with capacity \(K_j\) files the
   highest-priority eligible events, creating endogenous queue selection.
7. **Silence as a signal.** If the trigger is public, nonfiling is informative.
8. **Multiple regulatory tiers.** Issuer filings, LP obligations, and
   exchange-generated actions are distinct treatments with different first
   stages and selection problems.
'''

F["docs/IDENTIFICATION.md"] = r'''
# Identification hierarchy

## Legal audit first

No regression may label an event mandatory or noncompliant until the exact
rule, responsible party, deadline, episode treatment, exemptions, and effective
dates are verified from official sources.

## Denominator reconstruction

Build the full set of eligible product-days. Link filings through the legally
correct deadline, original/correction chains, and consecutive-event rule.
Distinguish timely filing, late filing, valid exemption, collection failure,
and unexplained nonfiling.

## Descriptive selection

Model filing among eligible events using severity, sign, issuer, benchmark,
asset class, episode status, stress, weekday, and operational congestion. This
is descriptive because latent event quality and filing cost are endogenous.

## Preferred causal design

Use only an externally validated enforcement, automation, vendor, outage, or
capacity shock. A date inferred from filing outcomes is invalid. Require flat
pretrends, a strong first stage, and exclusion restrictions.

## Multi-tier design

Analyze issuer filings, LP obligations, and exchange actions separately. Never
pool thresholds or responsible parties.

## Stop rules

Stop the top-journal claim when the legal duty is unverified, low compliance
vanishes after linkage corrections, no external shock exists, the first stage
is weak, or results depend on one issuer or episode.
'''

F["docs/LEGAL_AUDIT_TEMPLATE.md"] = '''# Legal audit template\n\nFor every threshold: responsible party; legal status; exact variable and timestamp; threshold; deadline; episode rule; correction rule; exemptions; sanctions; effective dates; official URL and document. Do not infer legal duty from a form title or news article.\n'''

F["docs/PREANALYSIS_PLAN.md"] = '''# Pre-analysis plan\n\nPrimary hypotheses: selective compliance survives legal and linkage corrections; an externally validated compliance shock increases timely filing; compliance changes market quality or investor attention; automation changes coverage and event composition. Primary outcomes: next-day absolute gap/mispricing, turnover/liquidity, retail flow when correctly measured, and repeat breach. Inference: issuer/date clustering, wild bootstrap, pretrend tests, weak-IV-robust intervals, and familywise correction.\n'''

F["docs/DATA_CONTRACTS.md"] = '''# Data contracts\n\nProduct-day fields: instrument_id, date, issuer_id, benchmark_id, market_scope, product_type, close, nav, official_gap, trading_value, volume, active, source_file, source_sha256. Disclosure fields: receipt_id, instrument_id, event_date, filing_timestamp, disclosure_type, correction linkage, source URL/hash, parser and validation status. Missing states: TIMELY_FILING, LATE_FILING, VALID_EXEMPTION, UNEXPLAINED_NONFILING, COLLECTION_FAILURE, RULE_UNVERIFIED, NOT_ELIGIBLE.\n'''

F["src/etf_compliance/__init__.py"] = '__version__ = "0.1.0"\n'

F["src/etf_compliance/utils.py"] = r'''
from __future__ import annotations
import hashlib, json, logging
from pathlib import Path
from typing import Any
import pandas as pd
import yaml

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path):
    p = Path(path); p.mkdir(parents=True, exist_ok=True); return p

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_table(path):
    p = Path(path)
    if p.suffix.lower() == ".parquet": return pd.read_parquet(p)
    if p.suffix.lower() in {".xlsx", ".xls"}: return pd.read_excel(p)
    if p.suffix.lower() == ".csv":
        last = None
        for enc in ("utf-8-sig", "euc-kr", "cp949", "utf-8"):
            try: return pd.read_csv(p, encoding=enc)
            except UnicodeDecodeError as e: last = e
        raise last
    raise ValueError(f"Unsupported file: {p}")

def write_json(obj, path):
    p = Path(path); ensure_dir(p.parent)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def logger(path):
    p = Path(path); ensure_dir(p.parent)
    log = logging.getLogger("etf_compliance"); log.setLevel(logging.INFO)
    if not log.handlers:
        fh = logging.FileHandler(p, encoding="utf-8"); sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt); sh.setFormatter(fmt); log.addHandler(fh); log.addHandler(sh)
    return log
'''

F["src/etf_compliance/schemas.py"] = r'''
class SchemaError(ValueError): pass

def require_columns(df, columns, name):
    missing = sorted(set(columns) - set(df.columns))
    if missing: raise SchemaError(f"{name} missing columns: {missing}")
'''

F["src/etf_compliance/ingest.py"] = r'''
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd
from .schemas import require_columns
from .utils import read_table, sha256_file

ALIASES = {
 "date": ["일자", "날짜", "거래일", "date"], "close": ["종가", "close"],
 "nav": ["순자산가치(NAV)", "순자산가치", "NAV", "nav"],
 "volume": ["거래량", "volume"], "trading_value": ["거래대금", "거래대금(원)", "trading_value"],
 "market_cap": ["시가총액", "market_cap"], "benchmark_name": ["지수명", "기초지수명", "benchmark_name"],
 "benchmark_close": ["기초지수 종가", "기초지수종가", "benchmark_close"]}

def norm(x): return re.sub(r"\s+", "", str(x)).lower()
def find_col(cols, aliases):
    lookup = {norm(c): c for c in cols}
    for a in aliases:
        if norm(a) in lookup: return lookup[norm(a)]
    return None

def infer_id(path, df):
    for c in df.columns:
        if norm(c) in {"종목코드", "단축코드", "instrument_id", "ticker"}:
            v = df[c].dropna().astype(str).str.extract(r"(\d{6})", expand=False).dropna()
            if len(v): return v.iloc[0].zfill(6)
    m = re.search(r"(?<!\d)(\d{6})(?!\d)", Path(path).name)
    if not m: raise ValueError(f"Cannot infer instrument ID from {path}")
    return m.group(1)

def ingest_product_day(path):
    p = Path(path); fs = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.suffix.lower() in {".csv", ".xlsx", ".xls", ".parquet"})
    frames = []
    for f in fs:
        raw = read_table(f); iid = infer_id(f, raw); rename = {}
        for k, aliases in ALIASES.items():
            c = find_col(list(raw.columns), aliases)
            if c: rename[c] = k
        df = raw.rename(columns=rename).copy(); require_columns(df, ["date", "close", "nav"], str(f))
        for c in ("close", "nav", "volume", "trading_value", "market_cap", "benchmark_close"):
            if c in df: df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False), errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce"); df["instrument_id"] = iid
        df["official_gap"] = df["close"] / df["nav"] - 1
        df["source_file"] = str(f); df["source_sha256"] = sha256_file(f); frames.append(df)
    if not frames: raise FileNotFoundError(path)
    return pd.concat(frames, ignore_index=True).dropna(subset=["date"]).drop_duplicates(["instrument_id", "date"], keep="last")

def ingest_disclosures(path):
    p = Path(path); fs = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.suffix.lower() in {".csv", ".xlsx", ".xls", ".parquet"})
    frames = []
    amap = {"receipt_id":["receipt_id","접수번호"],"instrument_id":["instrument_id","종목코드","단축코드"],"event_date":["event_date","발생일","기준일"],"filing_timestamp":["filing_timestamp","접수일시","공시시각"],"disclosure_type":["disclosure_type","공시유형","보고서명"],"is_correction":["is_correction","정정여부"],"original_receipt_id":["original_receipt_id","원접수번호"],"validation_status":["validation_status","검증상태"]}
    for f in fs:
        df = read_table(f); rename = {}
        for k, aliases in amap.items():
            for a in aliases:
                if a in df.columns: rename[a] = k; break
        frames.append(df.rename(columns=rename))
    if not frames: raise FileNotFoundError(path)
    out = pd.concat(frames, ignore_index=True); require_columns(out,["receipt_id","instrument_id","event_date","filing_timestamp","disclosure_type"],"disclosures")
    out["instrument_id"] = out["instrument_id"].astype(str).str.extract(r"(\d{6})", expand=False).str.zfill(6)
    out["event_date"] = pd.to_datetime(out["event_date"], errors="coerce"); out["filing_timestamp"] = pd.to_datetime(out["filing_timestamp"], errors="coerce")
    out["is_correction"] = out.get("is_correction", False).fillna(False).astype(bool); out["validation_status"] = out.get("validation_status", "UNVALIDATED")
    return out.dropna(subset=["receipt_id","instrument_id","event_date","filing_timestamp"])

def ingest_investor(path, side):
    p = Path(path); fs = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.suffix.lower() in {".csv", ".xlsx", ".xls", ".parquet"}); frames=[]
    for f in fs:
        raw=read_table(f); iid=infer_id(f,raw); dc=find_col(list(raw.columns),ALIASES["date"])
        if dc is None: raise ValueError(f"No date column: {f}")
        df=raw.rename(columns={dc:"date"}); vals=[c for c in df.columns if c!="date"]
        long=df.melt(id_vars=["date"],value_vars=vals,var_name="investor_group",value_name=f"{side}_value")
        long["date"]=pd.to_datetime(long["date"],errors="coerce"); long[f"{side}_value"]=pd.to_numeric(long[f"{side}_value"].astype(str).str.replace(",","",regex=False),errors="coerce"); long["instrument_id"]=iid; frames.append(long)
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=["instrument_id","date","investor_group",f"{side}_value"])

def reconcile_investor(buy,sell):
    keys=["instrument_id","date","investor_group"]; out=buy.merge(sell,on=keys,how="outer")
    if "buy_value" not in out: out["buy_value"]=np.nan
    if "sell_value" not in out: out["sell_value"]=np.nan
    out["net_buy_value"]=out["buy_value"]-out["sell_value"]; return out
'''

F["src/etf_compliance/legal.py"] = r'''
from __future__ import annotations
import pandas as pd
from .schemas import require_columns
class LegalAuditError(RuntimeError): pass

def validate_rules(df, require_verified=True):
    req=["rule_id","market_scope","product_type","threshold_abs","effective_start","filing_deadline_business_days","responsible_party","verified"]
    require_columns(df,req,"legal rules"); out=df.copy(); out["effective_start"]=pd.to_datetime(out["effective_start"],errors="coerce"); out["effective_end"]=pd.to_datetime(out.get("effective_end"),errors="coerce"); out["threshold_abs"]=pd.to_numeric(out["threshold_abs"],errors="coerce"); out["filing_deadline_business_days"]=pd.to_numeric(out["filing_deadline_business_days"],errors="coerce"); out["verified"]=out["verified"].astype(str).str.lower().map({"true":True,"false":False}).fillna(False)
    if require_verified and not out["verified"].all(): raise LegalAuditError("Unverified primary legal rule(s): "+", ".join(out.loc[~out["verified"],"rule_id"]))
    return out

def attach_rules(pdays,rules):
    rows=[]
    for _,r in rules.iterrows():
        m=pdays["market_scope"].eq(r["market_scope"]) & pdays["product_type"].eq(r["product_type"]) & pdays["date"].ge(r["effective_start"])
        if pd.notna(r["effective_end"]): m &= pdays["date"].le(r["effective_end"])
        p=pdays.loc[m].copy(); p["rule_id"]=r["rule_id"]; p["threshold_abs"]=r["threshold_abs"]; p["filing_deadline_business_days"]=r["filing_deadline_business_days"]; p["episode_rule"]=r.get("episode_rule","daily"); p["responsible_party"]=r["responsible_party"]; rows.append(p)
    out=pd.concat(rows,ignore_index=True) if rows else pdays.copy()
    if out.duplicated(["instrument_id","date"],keep=False).any(): raise LegalAuditError("Multiple rules apply to the same product-day")
    return out
'''

F["src/etf_compliance/linkage.py"] = r'''
from __future__ import annotations
import numpy as np
import pandas as pd

def add_bday(d,n): return pd.Timestamp(d)+pd.offsets.BDay(int(n))

def dedupe_docs(df):
    x=df.copy(); x["document_chain_id"]=x.get("original_receipt_id",x["receipt_id"]).fillna(x["receipt_id"]).astype(str); rank=x.get("validation_status","").astype(str).str.upper().map({"VALIDATED":2,"UNVALIDATED":1,"QUARANTINED":0}).fillna(1); x["rank"]=rank
    return x.sort_values(["document_chain_id","rank","filing_timestamp"]).groupby("document_chain_id",as_index=False).tail(1).drop(columns="rank")

def build_episodes(df,gap=1):
    x=df.sort_values(["instrument_id","date"]).copy(); ids=[]; cur=0; li=None; ld=None
    for r in x.itertuples():
        if r.instrument_id!=li or ld is None or len(pd.bdate_range(ld,r.date))-1>gap: cur+=1
        ids.append(f"E{cur:08d}"); li=r.instrument_id; ld=r.date
    x["episode_id"]=ids; return x

def link_filings(eligible,docs):
    x=eligible.copy(); x["deadline_date"]=[add_bday(d,n) for d,n in zip(x["date"],x["filing_deadline_business_days"])]; d=dedupe_docs(docs)
    m=x.merge(d,on="instrument_id",how="left",suffixes=("","_filing")); ok=m["filing_timestamp"].dt.normalize().ge(m["date"]) & m["filing_timestamp"].dt.normalize().le(m["deadline_date"])
    v=m.loc[ok].sort_values(["instrument_id","date","filing_timestamp"]).groupby(["instrument_id","date"],as_index=False).head(1)
    cols=["instrument_id","date","receipt_id","filing_timestamp","disclosure_type","document_chain_id"]
    out=x.merge(v[cols],on=["instrument_id","date"],how="left"); out["timely_filing"]=out["receipt_id"].notna(); out["filing_status"]=np.where(out["timely_filing"],"TIMELY_FILING","UNEXPLAINED_NONFILING"); return out
'''

F["src/etf_compliance/compliance.py"] = r'''
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

def eligibility(df):
    x=df.copy(); x["official_gap_abs"]=x["official_gap"].abs(); x["eligible"]=x["threshold_abs"].notna() & x["official_gap_abs"].ge(x["threshold_abs"]) & x.get("active",True); x["severity_ratio"]=x["official_gap_abs"]/x["threshold_abs"]; x["gap_sign"]=np.sign(x["official_gap"]).astype("Int64"); return x

def add_congestion(df):
    x=df.copy(); total=x.groupby(["issuer_id","date"])["eligible"].transform("sum"); x["issuer_day_eligible_count"]=total; x["leave_one_out_congestion"]=total-x["eligible"].astype(int); return x

def issuer_summary(df):
    g=df.groupby("issuer_id",dropna=False).agg(eligible_events=("eligible","sum"),timely_filings=("timely_filing","sum"),mean_severity=("severity_ratio","mean"),instruments=("instrument_id","nunique"),first_event=("date","min"),last_event=("date","max")).reset_index(); g["compliance_rate"]=g["timely_filings"]/g["eligible_events"].replace(0,np.nan); return g.sort_values("compliance_rate")

def diagnostics(df):
    e=df.loc[df["eligible"]]; s=issuer_summary(e); rate=e["timely_filing"].mean() if len(e) else np.nan; disp=100*(s["compliance_rate"].max()-s["compliance_rate"].min()) if len(s) else np.nan
    return {"eligible_events":int(len(e)),"timely_filings":int(e["timely_filing"].sum()),"compliance_rate":None if pd.isna(rate) else float(rate),"issuer_count":int(s["issuer_id"].nunique()),"issuer_dispersion_pp":None if pd.isna(disp) else float(disp)}

def selection_model(df):
    x=df.loc[df["eligible"]].copy(); x["year"]=x["date"].dt.year.astype(str); x["weekday"]=x["date"].dt.day_name(); f="timely_filing ~ np.log(severity_ratio) + C(gap_sign) + leave_one_out_congestion + C(issuer_id) + C(year) + C(weekday)"; m=smf.glm(f,data=x,family=sm.families.Binomial()).fit(cov_type="cluster",cov_kwds={"groups":x["issuer_id"]}); return m.summary2().tables[1].reset_index().rename(columns={"index":"term"}),m
'''

F["src/etf_compliance/causal.py"] = r'''
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import stats

@dataclass
class Result:
    term:str; coefficient:float; std_error:float; t_stat:float; p_value:float; nobs:int; clusters:int

def demean(df,cols,groups,iters=100,tol=1e-10):
    out=df[cols].astype(float).copy()
    for _ in range(iters):
        old=out.to_numpy(copy=True)
        for g in groups: out-=out.groupby(df[g]).transform("mean")
        if np.nanmax(np.abs(out.to_numpy()-old))<tol: break
    return out

def ols(X,y):
    inv=np.linalg.pinv(X.T@X); b=inv@X.T@y; return b,y-X@b

def cluster_cov(X,e,c):
    inv=np.linalg.pinv(X.T@X); meat=np.zeros((X.shape[1],X.shape[1])); u=pd.unique(c)
    for k in u:
        s=X[c==k].T@e[c==k]; meat+=np.outer(s,s)
    n,p=X.shape; adj=(len(u)/max(len(u)-1,1))*((n-1)/max(n-p,1)); return adj*inv@meat@inv

def two_way_cov(X,e,a,b):
    inter=np.array([f"{x}|{y}" for x,y in zip(a,b)]); return cluster_cov(X,e,a)+cluster_cov(X,e,b)-cluster_cov(X,e,inter)

def did(panel,outcome,treatment="shock_exposed",post="post_shock",fes=None,clusters=None):
    fes=fes or ["instrument_id","date"]; clusters=clusters or ["issuer_id","date"]; x=panel.dropna(subset=[outcome,treatment,post]+fes+clusters).copy(); x["did"]=x[treatment].astype(float)*x[post].astype(float); r=demean(x,[outcome,"did"],fes); y=r[outcome].to_numpy(); X=r[["did"]].to_numpy(); b,e=ols(X,y); cov=two_way_cov(X,e,x[clusters[0]].to_numpy(),x[clusters[1]].to_numpy()); se=float(np.sqrt(max(cov[0,0],0))); t=float(b[0]/se) if se else np.nan; g=min(x[clusters[0]].nunique(),x[clusters[1]].nunique()); p=float(2*stats.t.sf(abs(t),max(g-1,1))) if np.isfinite(t) else np.nan; return Result("did",float(b[0]),se,t,p,len(x),g)
'''

F["src/etf_compliance/shocks.py"] = r'''
from __future__ import annotations
import pandas as pd

def load_shocks(path):
    x=pd.read_csv(path)
    if x.empty: return x
    x["effective_date"]=pd.to_datetime(x["effective_date"],errors="coerce"); x["validated_external_source"]=x["validated_external_source"].astype(str).str.lower().map({"true":True,"false":False}).fillna(False); return x.loc[x["validated_external_source"]]

def attach(panel,shocks):
    if shocks.empty:
        x=panel.copy(); x["shock_exposed"]=False; x["post_shock"]=False; x["shock_id"]=pd.NA; return x
    rows=[]
    for _,s in shocks.iterrows():
        x=panel.copy(); x["shock_exposed"]=x["issuer_id"].astype(str).eq(str(s["issuer_id"])) if pd.notna(s["issuer_id"]) and str(s["issuer_id"]).strip() else True; x["post_shock"]=x["date"].ge(s["effective_date"]); x["shock_id"]=s["shock_id"]; x["shock_type"]=s["shock_type"]; rows.append(x)
    return pd.concat(rows,ignore_index=True)
'''

F["src/etf_compliance/theory.py"] = r'''
from dataclasses import dataclass
import numpy as np
@dataclass(frozen=True)
class FilingParameters:
    fixed_cost:float; reputation_cost:float; expected_flow_cost:float; detection_probability:float; sanction:float; latent_nonfiling_cost:float=0.0
def filing_cost(p): return p.fixed_cost+p.reputation_cost+p.expected_flow_cost
def nonfiling_cost(p): return p.detection_probability*p.sanction+p.latent_nonfiling_cost
def optimal_file(p): return nonfiling_cost(p)>=filing_cost(p)
def automation_counterfactual(p,reduction): return optimal_file(FilingParameters(max(0,p.fixed_cost-reduction),p.reputation_cost,p.expected_flow_cost,p.detection_probability,p.sanction,p.latent_nonfiling_cost))
def compliance_probability(costs,n): return float(np.mean(np.asarray(costs)<=n))
'''

F["src/etf_compliance/pipeline.py"] = r'''
from __future__ import annotations
from pathlib import Path
import pandas as pd
from .utils import load_config,ensure_dir,write_json,logger
from .ingest import ingest_product_day,ingest_disclosures,ingest_investor,reconcile_investor
from .legal import validate_rules,attach_rules,LegalAuditError
from .compliance import eligibility,add_congestion,issuer_summary,diagnostics,selection_model
from .linkage import build_episodes,link_filings
from .shocks import load_shocks,attach
from .causal import did

def save(df,path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix==".parquet": df.to_parquet(p,index=False)
    else: df.to_csv(p,index=False,encoding="utf-8-sig")

def run(config_path):
    c=load_config(config_path); out=ensure_dir(c["paths"]["outputs"]); proc=ensure_dir(c["paths"]["processed"]); log=logger(out/"logs"/"pipeline.log")
    pdays=ingest_product_day(c["paths"]["closing_premium"]); docs=ingest_disclosures(c["paths"]["kind"])
    defaults={"issuer_id":"UNKNOWN_ISSUER","benchmark_id":"UNKNOWN_BENCHMARK","market_scope":"foreign","product_type":"ETF","active":True}
    for k,v in defaults.items(): pdays[k]=pdays[k].fillna(v) if k in pdays else v
    rules_raw=pd.read_csv(c["paths"]["legal_rules"])
    try: rules=validate_rules(rules_raw,require_verified=not c.get("demo_mode",False)); legal=bool(rules["verified"].all()) or c.get("demo_mode",False)
    except LegalAuditError:
        if not c.get("demo_mode",False): raise
        rules=validate_rules(rules_raw,require_verified=False); legal=True
    risk=eligibility(attach_rules(pdays,rules)); e=build_episodes(risk.loc[risk["eligible"]],c["analysis"]["episode_gap_business_days"]); req=add_congestion(link_filings(e,docs))
    buy=ingest_investor(c["paths"]["investor_buy"],"buy"); sell=ingest_investor(c["paths"]["investor_sell"],"sell"); inv=reconcile_investor(buy,sell)
    save(pdays,proc/"product_day.parquet"); save(docs,proc/"disclosure_documents.parquet"); save(risk,proc/"eligibility_risk_set.parquet"); save(req,proc/"required_filings.parquet"); save(inv,proc/"investor_panel.parquet")
    d=diagnostics(req); save(issuer_summary(req),out/"tables"/"issuer_compliance_summary.csv"); sel,_=selection_model(req); save(sel,out/"tables"/"selection_function.csv"); write_json(d,out/"tables"/"diagnostics.json")
    shocks=load_shocks(c["paths"]["compliance_shocks"]); causal=[]; fstat=None
    if not shocks.empty:
        sp=attach(req,shocks); sp["filing_numeric"]=sp["timely_filing"].astype(float); r=did(sp,"filing_numeric"); causal.append(r.__dict__); fstat=r.t_stat**2
    save(pd.DataFrame(causal),out/"tables"/"first_stage.csv")
    a=c["analysis"]
    if not legal: verdict="STOP_NO_MANDATORY_RULE"
    elif d["eligible_events"]<a["min_eligible_events"]: verdict="STOP_COMPLIANCE_MEASUREMENT_ERROR"
    elif d["compliance_rate"]>=a["compliance_survival_threshold"]: verdict="STOP_SELECTIVE_COMPLIANCE_NOT_MATERIAL"
    elif d["issuer_dispersion_pp"]<a["issuer_dispersion_min_pp"]: verdict="STOP_ISSUER_DISPERSION_SMALL"
    elif shocks.empty: verdict="STOP_NO_EXOGENOUS_COMPLIANCE_SHOCK"
    elif fstat is None or fstat<a["min_shock_first_stage_f"]: verdict="STOP_WEAK_COMPLIANCE_SHOCK"
    else: verdict="PROCEED_CAUSAL_MARKET_EFFECTS"
    report=f"# GO / NO-GO\n\n- Legal verified: **{legal}**\n- Eligible events: **{d['eligible_events']}**\n- Compliance rate: **{d['compliance_rate']}**\n- Issuer dispersion (pp): **{d['issuer_dispersion_pp']}**\n- First-stage F: **{fstat}**\n\n## Verdict\n\n`{verdict}`\n"; (out/"GO_NO_GO.md").write_text(report,encoding="utf-8"); log.info(verdict); return report
'''

F["scripts/run_all.py"] = '''import argparse\nfrom etf_compliance.pipeline import run\nif __name__=="__main__":\n p=argparse.ArgumentParser(); p.add_argument("--config",default="config/project.yaml"); a=p.parse_args(); print(run(a.config))\n'''

F["scripts/make_demo_data.py"] = r'''
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1]; E=R/"examples"; E.mkdir(exist_ok=True); rng=np.random.default_rng(20260719); dates=pd.bdate_range("2024-01-01",periods=260); issuers=["ISSUER_A","ISSUER_B","ISSUER_C","ISSUER_D"]; rows=[]; docs=[]; buys=[]; sells=[]; receipt=100000
for ji,j in enumerate(issuers):
    adopt=dates[130] if j in {"ISSUER_A","ISSUER_B"} else pd.NaT
    for pi in range(6):
        iid=f"{ji+1}{pi:05d}"
        for date in dates:
            nav=10000+rng.normal(0,50); gap=rng.normal(0,.012)
            if rng.random()<.06: gap+=rng.choice([-1,1])*rng.uniform(.012,.04)
            close=nav*(1+gap); rows.append({"instrument_id":iid,"date":date,"issuer_id":j,"benchmark_id":f"BM_{pi%3}","market_scope":"foreign","product_type":"ETF","close":close,"nav":nav,"volume":rng.integers(1000,100000),"trading_value":rng.lognormal(15,1),"active":True})
            if abs(gap)>=.02:
                p={"ISSUER_A":.25,"ISSUER_B":.45,"ISSUER_C":.70,"ISSUER_D":.35}[j]+(.45 if pd.notna(adopt) and date>=adopt else 0); p=np.clip(p+.8*max(abs(gap)-.02,0),.01,.99)
                if rng.random()<p:
                    receipt+=1; docs.append({"receipt_id":str(receipt),"instrument_id":iid,"event_date":date,"filing_timestamp":date+pd.Timedelta(days=1,hours=8),"disclosure_type":"breach","is_correction":False,"original_receipt_id":"","validation_status":"VALIDATED"})
            buys.append({"instrument_id":iid,"date":date,"개인":rng.lognormal(13,.8)}); sells.append({"instrument_id":iid,"date":date,"개인":rng.lognormal(13,.8)})
pd.DataFrame(rows).to_csv(E/"demo_product_day.csv",index=False); pd.DataFrame(docs).to_csv(E/"demo_kind.csv",index=False); pd.DataFrame(buys).to_csv(E/"demo_investor_buy.csv",index=False); pd.DataFrame(sells).to_csv(E/"demo_investor_sell.csv",index=False); pd.DataFrame(columns=["instrument_id","date","action_type"]).to_csv(E/"demo_market_actions.csv",index=False)
pd.DataFrame([{"rule_id":"DEMO","market_scope":"foreign","product_type":"ETF","threshold_abs":.02,"threshold_unit":"decimal","effective_start":"2024-01-01","effective_end":"","filing_deadline_business_days":1,"episode_rule":"daily","responsible_party":"issuer","legal_status":"DEMO","verified":True,"source_url":"https://example.invalid/rule","source_document":"Synthetic","notes":"demo"}]).to_csv(E/"demo_legal_rules.csv",index=False)
pd.DataFrame([{"shock_id":"AUTO_A","issuer_id":"ISSUER_A","shock_type":"automation","announcement_date":dates[125],"effective_date":dates[130],"validated_external_source":True,"source_url":"https://example.invalid/a","expected_first_stage_direction":"positive","notes":"demo"},{"shock_id":"AUTO_B","issuer_id":"ISSUER_B","shock_type":"automation","announcement_date":dates[125],"effective_date":dates[130],"validated_external_source":True,"source_url":"https://example.invalid/b","expected_first_stage_direction":"positive","notes":"demo"}]).to_csv(E/"demo_shocks.csv",index=False)
print("demo data created")
'''

F["tools/krx_manual_session_downloader.py"] = r'''
"""Conservative optional helper. Manual login; no bypass; no stealth.
Researchers must inspect the current official DOM and fill selectors locally.
The script stops instead of probing an unknown page repeatedly."""
from pathlib import Path
import argparse,json,random,time

def main():
 p=argparse.ArgumentParser(); p.add_argument("--profile",required=True); p.add_argument("--instruments",required=True); p.add_argument("--download-dir",required=True); p.add_argument("--min-delay",type=float,default=12); p.add_argument("--max-delay",type=float,default=20); a=p.parse_args()
 try: from playwright.sync_api import sync_playwright
 except ImportError: raise SystemExit("pip install playwright && playwright install chromium")
 ids=[x.strip() for x in Path(a.instruments).read_text().splitlines() if x.strip()]; out=Path(a.download_dir); out.mkdir(parents=True,exist_ok=True); manifest=out/"manifest.jsonl"
 selectors={"instrument_input":"","search_button":"","csv_button":""}
 if not all(selectors.values()): raise SystemExit("Inspect the official current page and fill selectors in a local copy. Guessing is disabled.")
 with sync_playwright() as pw:
  ctx=pw.chromium.launch_persistent_context(a.profile,headless=False,accept_downloads=True); page=ctx.pages[0] if ctx.pages else ctx.new_page(); page.goto("https://data.krx.co.kr/"); input("Log in and navigate to the official page; press Enter here: ")
  for iid in ids:
   try:
    page.locator(selectors["instrument_input"]).fill(iid); page.locator(selectors["search_button"]).click(); page.wait_for_load_state("networkidle")
    with page.expect_download() as info: page.locator(selectors["csv_button"]).click()
    target=out/f"{iid}_{info.value.suggested_filename}"; info.value.save_as(target); rec={"instrument_id":iid,"status":"ok","path":str(target)}
   except Exception as e: rec={"instrument_id":iid,"status":"error","error":str(e)}
   with manifest.open("a",encoding="utf-8") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
   if rec["status"]!="ok": raise SystemExit(rec)
   time.sleep(random.uniform(a.min_delay,a.max_delay))
  ctx.close()
if __name__=="__main__": main()
'''

F["tests/test_theory.py"] = '''from etf_compliance.theory import *\ndef test_rule():\n p=FilingParameters(1,1,1,.8,5); assert filing_cost(p)==3 and nonfiling_cost(p)==4 and optimal_file(p)\ndef test_automation():\n p=FilingParameters(5,1,1,.5,10); assert not optimal_file(p); assert automation_counterfactual(p,3)\n'''

F["tests/test_eligibility.py"] = '''import pandas as pd\nfrom etf_compliance.compliance import eligibility\ndef test_threshold():\n d=pd.DataFrame({"official_gap":[.019,.02,-.021],"threshold_abs":[.02]*3,"active":[True]*3}); assert eligibility(d)["eligible"].tolist()==[False,True,True]\n'''

F["tests/test_linkage.py"] = '''import pandas as pd\nfrom etf_compliance.linkage import link_filings\ndef test_deadline():\n e=pd.DataFrame({"instrument_id":["000001","000002"],"date":pd.to_datetime(["2026-01-05"]*2),"filing_deadline_business_days":[1,1]}); d=pd.DataFrame({"receipt_id":["A","B"],"instrument_id":["000001","000002"],"event_date":pd.to_datetime(["2026-01-05"]*2),"filing_timestamp":pd.to_datetime(["2026-01-06 08:00","2026-01-08 08:00"]),"disclosure_type":["breach"]*2,"is_correction":[False]*2,"validation_status":["VALIDATED"]*2}); o=link_filings(e,d).set_index("instrument_id"); assert o.loc["000001","timely_filing"] and not o.loc["000002","timely_filing"]\n'''

F["tests/test_causal.py"] = '''import numpy as np,pandas as pd\nfrom etf_compliance.causal import did\ndef test_did():\n r=np.random.default_rng(7); rows=[]; dates=pd.date_range("2025-01-01",periods=30)\n for i in range(30):\n  for t,d in enumerate(dates): rows.append({"instrument_id":f"P{i}","issuer_id":f"I{i%10}","date":d,"shock_exposed":i<15,"post_shock":t>=15,"y":.5*(i<15)*(t>=15)+r.normal(0,.2)})\n assert did(pd.DataFrame(rows),"y").coefficient>.3\n'''

F["tests/test_demo.py"] = '''from pathlib import Path\nimport subprocess,sys\ndef test_demo():\n r=Path(__file__).resolve().parents[1]; subprocess.run([sys.executable,"scripts/make_demo_data.py"],cwd=r,check=True); subprocess.run([sys.executable,"scripts/run_all.py","--config","config/demo.yaml"],cwd=r,check=True); assert (r/"outputs"/"GO_NO_GO.md").exists()\n'''

F[".gitignore"] = '''__pycache__/\n.pytest_cache/\n*.pyc\n.env\ndata/raw/*\n!data/raw/**/.gitkeep\ndata/interim/*\n!data/interim/.gitkeep\ndata/processed/*\n!data/processed/.gitkeep\noutputs/*\n!outputs/**/.gitkeep\nplaywright-profile/\n'''

for rel, content in F.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

for d in ROOT.rglob("*"):
    if d.is_dir() and not any(d.iterdir()):
        (d / ".gitkeep").write_text("", encoding="utf-8")

with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(ROOT.rglob("*")):
        if p.is_file():
            zf.write(p, p.relative_to(ROOT.parent))

sha = hashlib.sha256(ZIP.read_bytes()).hexdigest()
Path("PACKAGE_SHA256.txt").write_text(f"{sha}  {ZIP.name}\n", encoding="utf-8")
print(f"built {ZIP} ({ZIP.stat().st_size} bytes), sha256={sha}")
