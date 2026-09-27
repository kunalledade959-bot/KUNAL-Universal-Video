# KUNAL Story Worker extension

Install this extension manually in Chrome/Chromium developer mode for local testing.

The extension only provides the tab/session control boundary. A site-specific content adapter must be added for each compatible generator. It must stop on CAPTCHA, required login, rate limits, or automation restrictions. It must never bypass them.

Next adapter contract:
- detectReady()
- submitBatch(frameJobs)
- collectOutputs()
- reportBlocked(reason)
- reportFailed(frameIds)
