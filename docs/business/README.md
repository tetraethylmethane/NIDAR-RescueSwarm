# RescueSwarm — Business Strategy (Phase 4B)

**200 points — exactly as many as the entire Design Review, and 20 % of the
1000-point total.** Nothing in this repository addressed it before this file
existed. It is scored as a startup pitch (4.22): the team presents its drone
system as a viable business proposition, 15 minutes plus 10 for questions.

**This is a skeleton, not an answer.** Each section states what is scored, what
we can already support from work in this repo, and what has to be gathered.
Items marked ⏳ have **lead time** and cannot be produced in the final week.

---

## Scored parameters (rulebook §9, M1 Phase 4B)

| # | Parameter | Max | Status |
|---|---|---|---|
| 1 | Problem Understanding & Real-World Relevance | 30 | Strong — see §1 |
| 2 | Target Users, Customers & Beneficiaries | 20 | To draft |
| 3 | Market Sizing & Deployment Potential | 30 | To research — sources named in [cost-and-economics.md](cost-and-economics.md) §5 |
| 4 | Business Model & Revenue Approach | 30 | Cost basis ready (14.60 L/system); pricing needs §5 inputs |
| 5 | Expenditure Breakdown & Resource Planning | 20 | ✅ **Done** — [cost-and-economics.md](cost-and-economics.md), generated from the BOM |
| 6 | Funds Raised, Sponsorships & Resource Mobilisation | 20 | ⏳ **Lead time** |
| 7 | Competitive Advantage & Differentiation | 20 | Strong — see §7 |
| 8 | Go-to-Market Strategy & Partnership | 20 | ⏳ Partner conversations have lead time |
| 9 | Regulatory, Safety & Adoption Readiness | 10 | To draft — DGCA framework |

---

## 1. Problem understanding (30)

The strongest section, because it is already evidenced. Flood response in India
is a recurring, quantifiable problem, and the engineering work in
[`../sizing/`](../sizing/) demonstrates understanding well beyond the pitch level.

**Use the engineering as proof of understanding.** The five findings in the
README — that the mission is not coverage-limited, that setup is the only tight
constraint, that release velocity dominates drop accuracy — are exactly the kind
of non-obvious insight that distinguishes a team that has actually modelled the
problem from one that has described it.

**To gather:** NDRF/SDRF deployment statistics, flood-affected area and
displacement figures for recent Indian flood events, current search-and-rescue
response times.

## 2. Target users (20)

Candidate segments, to be narrowed to a primary:
- **NDRF / SDRF** — national and state disaster response forces
- **District disaster management authorities** — first responders on scene
- **Coast Guard and inland waterway authorities**
- **Large industrial sites** with on-site emergency response obligations

Distinguish **buyer** (procurement authority), **user** (the two-person crew),
and **beneficiary** (survivors). The scoring lists all three.

## 3. Market sizing (30)

Build **bottom-up**, not top-down — bottom-up sizing is far more defensible under
questioning. Structure: number of districts with flood exposure × systems per
district × replacement cycle, plus a services/training component. State the
assumptions explicitly and show the sensitivity.

**To research:** Indian drone market size and growth, government disaster
management budget allocations, existing procurement precedents.

## 4. Business model (30)

Options to evaluate — pick one and defend it:
- **Hardware sale** with annual maintenance
- **Lease / drone-as-a-service** to district authorities
- **Capability contract** — guaranteed response readiness

The indigenisation position matters commercially, not only for scoring: public
procurement in India increasingly favours domestic content, so the 95.5 % Indian
supplier figure is a **sales argument**, not just a compliance one.

## 5. Expenditure breakdown (20) — ⚠ required deliverable

Rule 7.5 requires **a detailed cost sheet in addition to the BOM**. The BOM
exists in [`../../hardware/bom/`](../../hardware/bom/); the cost sheet does not.

See [`cost-sheet.md`](cost-sheet.md) for the required structure. It must cover
all costs incurred in designing, developing, integrating and testing — not just
flight hardware. Development tooling, test consumables, travel to the finals and
crashed-airframe replacements all count and are commonly forgotten.

## 6. Funds raised and sponsorship (20) — ⏳ lead time

**Start now.** This is the section most likely to score zero by default, and the
only one that cannot be written up at the last minute. Institutional grants,
departmental support, component sponsorship from Indian suppliers already on the
BOM, and incubator support all count. Suppliers listed in the README
(Bharath Components, Mechtex, Flameback Tech, Zuppa, e-con Systems, and others)
have a direct interest in an indigenous system that showcases their parts.

**Keep evidence** — emails, letters of support, invoices. Claims without
evidence do not score.

## 7. Competitive advantage (20)

The genuine differentiators, all evidenced in this repo:
- **A closed engineering model** where every published number is reproducible
  from committed code. Very few student teams can say this.
- **Read-only GCS by construction** — the rule violation is structurally
  impossible rather than avoided by discipline.
- **Indigenous supply chain** with an honest dual-basis score (95.5 % of line
  items, 60.2 % of value) rather than a single flattering number.
- **Decisions traceable to analysis**, including documented reversals — see
  [`../sizing/configuration-trade.md`](../sizing/configuration-trade.md).

Honesty about what is *not* Indian (AI inference silicon, high-drain cells, RF
chipsets, high-current connectors) is a credibility asset under jury
questioning, not a weakness.

**Name the two deliberate scope limits before a juror finds them**, so they read
as engineering judgement rather than oversight:

- **RGB-only sensing.** Correct for this competition — the targets are
  human-looking dummies scored in daylight, and thermal detects body heat a
  mannequin does not have. For real flood response, thermal is a genuine
  roadmap item: live humans emit heat and it works at night.
- **GNSS-dependent navigation.** The 450-point accuracy case rests on RTK. Real
  deployments face jamming, urban canyon and indoor voids — and NIDAR's own
  Mission 2 is explicitly GPS-denied. Visual-inertial odometry as a GNSS
  fallback is the natural next capability, and saying so costs nothing now.

## 8. Go-to-market (20) — ⏳ partner lead time

Pilot-first: one district authority, one monsoon season, measured outcomes.
Identify a named partner if at all possible — a real letter of intent scores
very differently from a hypothetical.

## 9. Regulatory and adoption readiness (10)

Cover the **DGCA Drone Rules 2021** framework: UIN registration, remote pilot
certification, airspace zones (green/yellow/red), and BVLOS status. Note honestly
where autonomous swarm operation sits relative to current regulation and what
would be required for operational deployment.

---

## Preparation sequence

| When | Action |
|---|---|
| **Now (P0–P1)** | Begin sponsorship and institutional-funding conversations (§6). Longest lead. |
| P1–P2 | Start the cost sheet and keep it current as procurement happens — reconstructing it later is far harder |
| P3 (Oct review) | Draft market sizing and business model |
| P4–P6 | Partner and pilot conversations (§8) |
| P8 (Dec review) | Full draft, rehearsed |
| P10 | Final rehearsal with Q&A practice — 10 of the 25 minutes are questions |
