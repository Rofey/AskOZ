"""Protection against abuse and runaway cost.

AskOz's main risk isn't downtime, it's "denial of wallet": every answer costs
real money in Claude usage, so unlimited questions mean an unlimited bill.
The layers here (rate limits, a daily spend cap, an answer cache) sit behind
Cloudflare, which handles network-level floods that app code can't.
"""
