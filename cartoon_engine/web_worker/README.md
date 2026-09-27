# Browser Worker

A policy-safe browser worker layer for the Story-to-Video engine.

It is designed to control user-authorized browser tabs and collect outputs from compatible generators. It must stop on CAPTCHA, mandatory login, rate limits, ambiguous output mapping, or a site that disallows automation. It never bypasses those controls.

Architecture:
Story Director -> Job Queue -> Worker 1..5 -> Backend Adapter -> Verify -> Retry Queue.

This folder is the browser-worker contract and local controller boundary. The actual browser extension can be implemented as Manifest V3.
