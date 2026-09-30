# Microsoft Foundry one-day workshop

A customer-neutral workshop for professional builders: see an agent in action,
build and evaluate it, then connect the experience to production architecture.
All exercises use fictional data. This is a development baseline, not a fully
qualified delivery package; only Labs 2 and 3 are currently published.

## Start here

- [Workshop labs](docs/index.html)
- [Lab 2: Build an agent](docs/guides/chapter-2-build-agent.html)
- [Lab 3: Evaluate and improve](docs/guides/chapter-3-evaluate-agent.html)
- [Workshop sequence](AGENDA.md)
- [Synthetic instrument PDF corpus](data/instruments/) · [Grounding eval dataset](evals/grounding/)

## Delivery and maintenance

- [Active roadmap](PLAN.md)
- [Local validation and live qualification limits](teacher/VALIDATION.md)
- [Repository instructions](AGENTS.md) · [Architecture decisions](docs/adr/)

## Preview

Open `docs\index.html`, or run from the repository root:

```powershell
python -m http.server 4173 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:4173/`; stop with Ctrl+C. Serve only `docs`, never the
repository root or private `.workshop` state. File and HTTP origins keep separate
browser-local worksheet and theme storage. Prepared-seat readiness is a separate
facilitator check, not a consequence of opening a guide.
