# Daytona — Cached Reference

Source: https://www.daytona.io/pricing, https://github.com/daytonaio/daytona, https://www.daytona.io/docs/en/oss-deployment/
Retrieved: 2026-05-18

## Model
- Hosted + open-source (AGPL 3.0). Hybrid mode: Daytona orchestrates sandboxes that execute on infra you control.

## Isolation
- Docker containers by default (not microVMs). Marketing claims "dedicated kernel, filesystem, network stack" — verify per deployment mode. [UNVERIFIED claim of dedicated kernel in default container mode]
- Cold start ~27–90 ms — fastest of the major hosted providers.

## Filesystem & Sessions
- Sandboxes can be paused/resumed. Unlimited session duration.

## Pricing (cloud)
- $0.0504 / vCPU-hour, $0.0162 / GiB-hour. Per-second metering.
- $200 free compute + 5 GiB storage. Startup credits up to $50K.

## Self-host
- Open source under AGPL 3.0; Caddy + Let's Encrypt deployment path documented; runs on a single server with a public domain.

## Trade-offs
- Faster than E2B for high-RPS workloads.
- Weaker isolation than microVMs when run in default container mode; security depends on host kernel.
