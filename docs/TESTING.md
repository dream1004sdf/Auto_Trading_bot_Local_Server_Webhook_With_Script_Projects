# Test evidence and limitations

This page records verifiable test runs instead of estimated performance claims. The latest CI state can be checked at the linked GitHub Actions workflow.

## Confirmed historical run

- **Workflow:** [Python tests](https://github.com/dream1004sdf/Auto_Trading_bot_Local_Server_Webhook_With_Script_Projects/actions/runs/39345316766)
- **Environment:** GitHub-hosted Ubuntu, CPython **3.11.17**
- **Dependency:** Flask **3.1.3**
- **Command:** `python -m pytest -q`
- **Result:** **10 passed in 0.47s** (GitHub Actions log, October 19, 2026 U.S. Eastern / October 20 UTC)
- **Scope:** Earlier initial suite. This is not a result for the expanded test file or Windows matrix.

## Verified expanded cross-platform test run

The expanded suite contains **20 tests** and the new CI matrix runs it in **four distinct environments**, totaling **80 successful test executions** in the referenced run.

**Evidence:** [GitHub Actions run #39346110321](https://github.com/dream1004sdf/Auto_Trading_bot_Local_Server_Webhook_With_Script_Projects/actions/runs/39346110321). Each job ran `python -m py_compile Server.py` and `python -m pytest -q`; all jobs concluded **success**.

| Runner | CPython | pytest summary | Outcome |
| --- | --- | --- | --- |
| Ubuntu Linux | 3.11.17 | 20 passed in 0.51s | Success |
| Ubuntu Linux | 3.12.15 | 20 passed in 0.46s | Success |
| Windows | 3.11.9 | 20 passed in 0.58s | Success |
| Windows | 3.12.10 | 20 passed in 0.67s | Success |

The exact results above describe a completed CI snapshot; they are **not a claim about future builds**. The current status is available on the [GitHub Actions workflow page](https://github.com/dream1004sdf/Auto_Trading_bot_Local_Server_Webhook_With_Script_Projects/actions/workflows/tests.yml).

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Test areas

| Area | Verification method |
| --- | --- |
| Flask service health | HTTP test client |
| Webhook token and malformed JSON | Success and rejection cases |
| Secret filtering | Unit test for database fields |
| Simulated order validation | Valid and invalid trade requests |
| Mathematical indicators | Constructed rising, flat, short-history data |
| Optional DB code path | Mocked client, success and unavailable paths |
| No live wallet | HTTP 501 contract |
| Import / syntax | `py_compile` in CI |

## Explicitly not verified by these tests

- Integration against a real InfluxDB instance
- Actual TradingView webhook delivery across the internet
- Brokerage API access or real orders (intentionally disabled)
- Profitability or backtesting correctness
- All historical Pine Script files compiling under TradingView

**Interpretation:** A passing CI build verifies the tested code paths on the specific runner, not general production readiness.

## Security note

Existing public Git history predates these changes. If any previously published webhook token or key was valid, revoke/rotate it. Updating or deleting the latest file does not erase historical commits.
