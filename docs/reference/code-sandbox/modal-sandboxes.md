# Modal Sandboxes — Cached Reference

Source: https://modal.com/products/sandboxes, https://modal.com/pricing
Retrieved: 2026-05-18

## Model
- Hosted only (no self-host). Built on gVisor.
- Scales to 50,000+ concurrent sandboxes; sub-second cold start typical.

## Isolation
- gVisor user-space kernel (runsc-style). Lighter than microVMs but still kernel-surface reducing.
- I/O-heavy workloads: 20–50% overhead typical.

## Networking
- Full block or CIDR allowlist. Tunnels for direct connectivity.

## GPU
- Only major hosted sandbox provider that supports GPU inside a sandbox in 2026 (A100, H100).
- GPU billed at standard Modal compute rate (no sandbox premium); CPU/mem sandbox-premium applies.

## Pricing
- Sandboxes: $0.00003942 / core-sec ≈ $0.142/physical-core/hour (~$0.071/vCPU-hour effective). Memory $0.00000672/GiB-sec.
- 3x premium vs standard Modal Functions.
- $30/month free credits.

## Notes
- Best for ML agents that need GPU inside the same sandbox.
- No self-host; vendor lock-in.
