# Resume / Portfolio Material

This file isn't part of the codebase — it's copy you can lift directly for
your resume, LinkedIn, or a portfolio site. Swap in real numbers once you've
run this against real (de-identified/aggregated) scheduling data if you're
able to; otherwise the synthetic-dataset numbers below are accurate to what's
in this repo and safe to cite as-is.

---

## One-line project summary

**OR Utilization Analytics Tool** — Python toolkit that analyzes procedure
room scheduling data to quantify utilization, turnaround time, delays,
overruns, and cancellations, and simulates process-improvement scenarios to
estimate additional case capacity within existing operating hours.

## Resume bullet options (pick 2–3, tune to the role)

**For a data analyst / healthcare analytics role:**
> Built an open-source Python analytics tool that computes operating-room
> utilization, turnaround time, and cancellation metrics from scheduling
> data, and simulates process-improvement scenarios estimating 100+
> additional case-equivalents per month achievable without added operating
> hours — informed by hands-on experience in a hospital surgery department.

**For a software engineering role:**
> Designed and built a modular Python package (pandas/numpy/matplotlib) with
> a CLI, automated report generation, and a 30+ test pytest suite covering
> a metrics engine and a transparent simulation model; set up CI via GitHub
> Actions across 3 Python versions.

**For a healthcare operations / process improvement role:**
> Created a data-driven simulation model translating operational levers
> (turnaround time, start-delay, overrun reduction) into estimated
> utilization gains and additional procedure capacity, designed to support
> concrete conversations with OR leadership about block-time allocation.

**Shorter, generic version:**
> Built and open-sourced a Python tool for analyzing procedure-room
> scheduling data (utilization %, delays, overruns, cancellations,
> turnaround time) with a "what-if" simulator estimating added capacity from
> process improvements — motivated by firsthand experience in a hospital
> surgery department.

## Talking points for an interview

- **The problem:** OR time is one of the most expensive and hardest-to-see
  resources in a hospital. Utilization is usually reported as one blended
  number; the interesting story is almost always in the breakdown — which
  rooms, which blocks, which time of day are losing capacity, and to what
  (late starts vs. slow turnovers vs. overruns vs. cancellations look
  identical in a single utilization percentage but need completely
  different fixes).
- **The technical approach:** cleanly separated the concerns — a loader that
  validates and infers with visible logging (no silent defaults), a metrics
  engine that's pure pandas/numpy with unit-testable, hand-verifiable
  outputs, and a simulation layer that is deliberately *not* a black box —
  every estimated number traces back to a named assumption you could show
  to a non-technical stakeholder and defend line by line.
- **What you'd do differently at scale / with real data:** add case-mix
  awareness to the simulator (a 3-hour spine case can't fill a 45-minute
  gap), pull in EHR/scheduling-system data directly instead of CSV export,
  and validate the turnaround/delay distributions against literature
  benchmarks (e.g., AORN or published OR-efficiency studies) rather than
  synthetic assumptions.
- **Why you're the right person to build this:** direct exposure to the
  operational reality of a surgery department (Northside) — not just the
  dataset, but the workflow behind it (block scheduling, add-on cases,
  turnover logistics) — which shaped what metrics actually matter and what
  a "believable" simulation assumption looks like.

## Suggested repo polish before sharing the link

- [ ] Replace `YOUR_USERNAME` in `README.md` badges with your actual GitHub username.
- [ ] Replace `Your Name` in `pyproject.toml` and `LICENSE` with your name.
- [ ] Push to GitHub, confirm the CI badge goes green.
- [ ] Pin the repo on your GitHub profile and add topics: `healthcare-analytics`,
      `operating-room`, `data-analysis`, `python`, `pandas`, `simulation`.
- [ ] Optional: deploy the notebook read-only via nbviewer or add a
      screenshot of the generated report to the README for visual impact.
