## Why

<!-- Business motivation / problem being solved. -->

## What changed

<!-- Keep mechanical normalization separate from behavioral changes where possible. -->

## Risk

- [ ] ACLs / record rules / groups
- [ ] `sudo()` / privilege changes
- [ ] public/portal controllers or RPC surface
- [ ] raw SQL / dynamic evaluation
- [ ] external network/API calls
- [ ] filesystem / subprocess
- [ ] cron/background jobs
- [ ] sensitive/customer data
- [ ] accounting/payment/authentication
- [ ] none of the above

## Verification

- [ ] static CI
- [ ] tests added/updated where behavior changed
- [ ] security review needed/performed if risk warrants it
- [ ] Workbench/UAT performed if this change reached the runtime verification stage
