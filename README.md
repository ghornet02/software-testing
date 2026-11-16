# Software Testing

Three Python test suites, each using a different testing technique on a different system:

| Suite | Technique | System under test | Tests |
|---|---|---|---|
| [`blackbox-testing`](blackbox-testing) | Black-box API testing | QuickCart e-commerce REST API | 105 |
| [`integration-testing`](integration-testing) | Integration testing | StreetRace Manager (8 interacting modules) | 43 |
| [`whitebox-testing`](whitebox-testing) | White-box and branch-coverage testing | MoneyPoly board game engine | 39 |

All suites use **pytest**.

## Requirements

- Python 3.10+
- `pytest`
- `requests` (black-box suite only)

```sh
python3 -m pip install pytest requests
```

## Black-box testing: QuickCart API

These tests check a running QuickCart server purely against its specification. They cover authentication headers, products, the cart, checkout, the wallet, addresses, reviews, orders, the profile, coupons, loyalty points and support-ticket state transitions. Each test checks status codes and response bodies, including boundary and invalid inputs.

```sh
cd blackbox-testing
pytest -q tests/test_quickcart.py     # expects the API at http://localhost:8080/api/v1
```

## Integration testing: StreetRace Manager

StreetRace Manager is a modular system for running a racing crew. Its modules are registration, crew management, inventory, race management, results, mission planning, vehicle maintenance and the leaderboard. The **vehicle maintenance** and **leaderboard** modules were designed and built as part of this project.

The 43 integration tests wire the real modules together and check how they interact. They cover:
- role checks across modules
- car status transitions (`ready`, `damaged`, `maintenance`)
- parts, tools and cash used by maintenance
- consistency between results and the leaderboard
- rollback when a multi-module operation fails part-way

```sh
cd integration-testing
PYTHONPATH=. pytest -q
PYTHONPATH=. python3 -m streetrace.main    # end-to-end demo
```

The report and the module call graph are in `report.pdf` and `diagrams/CallGraph.pdf`.

## White-box testing: MoneyPoly

MoneyPoly is a property-trading board game engine. The tests were written from its source code to reach full branch coverage of turns, doubles and jail, rent, mortgages, trades, auctions, cards, bankruptcy and the interactive menus. Randomness and user input are replaced with stubs and `monkeypatch`. The report documents the bugs the tests found and the pylint cleanup passes.

```sh
cd whitebox-testing
pytest -q
PYTHONPATH=src python3 src/main.py         # play the game
```

The report and the control-flow graph are in `report.pdf` and `diagrams/controlFlowGraph.pdf`.

## Project structure

```
blackbox-testing/tests/        QuickCart API tests
integration-testing/streetrace/ StreetRace Manager modules
integration-testing/tests/     Integration tests
whitebox-testing/src/moneypoly/ MoneyPoly engine
whitebox-testing/tests/        White-box tests
```
