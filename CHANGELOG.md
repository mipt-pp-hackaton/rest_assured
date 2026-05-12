# CHANGELOG

<!-- version list -->

## v1.2.1 (2026-05-12)

### Bug Fixes

- Rollback chages
  ([`1012249`](https://github.com/mipt-pp-hackaton/rest_assured/commit/1012249a30fe6cb6dc72cfc35983d8ff28ce4866))

- Update postgres healthcheck username in docker-compose and document environment requirements in
  README
  ([`6ab80f3`](https://github.com/mipt-pp-hackaton/rest_assured/commit/6ab80f36d2e1659ad7eb1338473879d2feb13de7))

### Chores

- Auto format
  ([`30ff932`](https://github.com/mipt-pp-hackaton/rest_assured/commit/30ff932f94b87e79d64882e1999f48f336b150ac))

### Refactoring

- Clean up code formatting and imports across configuration and database modules
  ([`f81d9a1`](https://github.com/mipt-pp-hackaton/rest_assured/commit/f81d9a1e6d4621d59da2a3b2f790c99661fa88da))

- Configure NullPool for testcontainers, reset database tables in integration tests, and update db
  driver and execution method
  ([`98f8372`](https://github.com/mipt-pp-hackaton/rest_assured/commit/98f837256647c5e9a329940e211298fb5d65085c))

- Update service models and remove obsolete settings loader test
  ([`1176b6c`](https://github.com/mipt-pp-hackaton/rest_assured/commit/1176b6c1ec4d900744801b9b8ffd521689804ffb))

- Update Settings model instantiation to use app_settings and db_settings keys
  ([`d3cf1d0`](https://github.com/mipt-pp-hackaton/rest_assured/commit/d3cf1d04d3a6ebbd35805d84b8057576fb30ed3e))

- Update test configuration to use updated settings schema and simplify async session management
  ([`fa65873`](https://github.com/mipt-pp-hackaton/rest_assured/commit/fa65873151daf0093b88b300b46324bbe608628f))


## v1.2.0 (2026-05-10)

### Bug Fixes

- Ci
  ([`eebad13`](https://github.com/mipt-pp-hackaton/rest_assured/commit/eebad1396ed33238187739db4861e17fd8c4e016))

- Reformat
  ([`ceadefe`](https://github.com/mipt-pp-hackaton/rest_assured/commit/ceadefed7cb5f5c1d07e9c4f13a6daead1b44f71))

- **epic-2**: Address PR review findings for health-checking scheduler
  ([`d206984`](https://github.com/mipt-pp-hackaton/rest_assured/commit/d206984b9474565496a06b45578ed8d2970b70b1))

### Chores

- Update gitignore
  ([`7678c06`](https://github.com/mipt-pp-hackaton/rest_assured/commit/7678c06cc814f57a8ad4df328895110db6564a0a))

### Refactoring

- Clean up imports and improve code readability in various modules
  ([`4848e39`](https://github.com/mipt-pp-hackaton/rest_assured/commit/4848e39912881fcb86d2bb6ecb0eb6ce6a0cbc85))

- Update test imports and improve readability in scheduler tests
  ([`1694728`](https://github.com/mipt-pp-hackaton/rest_assured/commit/1694728fa786cc4731f5d6b250f62a9f88d9fe1a))


## v1.1.0 (2026-05-10)

### Chores

- Remove docker image build and push job from CI workflow
  ([`fc7caef`](https://github.com/mipt-pp-hackaton/rest_assured/commit/fc7caef7018a0857711c9742f8261d10cda58dcf))

- Update actions/checkout and actions/setup-python to version 6
  ([`808eab8`](https://github.com/mipt-pp-hackaton/rest_assured/commit/808eab862bc04ba83e8721892eb89fdf57e25477))

- Upgrade actions/checkout and actions/setup-python to version 6 across CI workflows
  ([`17f2c8d`](https://github.com/mipt-pp-hackaton/rest_assured/commit/17f2c8d03dc94ed5cd25eca3c15fcb98f1a272b6))

### Documentation

- Add contributor workflow guide for issues, branches and PRs
  ([`fd9e988`](https://github.com/mipt-pp-hackaton/rest_assured/commit/fd9e9884411fac2344ae9042f13cf9d0cf6838d5))

- Expand contributor guide with detailed Conventional Commits section
  ([`68c585a`](https://github.com/mipt-pp-hackaton/rest_assured/commit/68c585ad314e0ed424e27a4ea1ea182d412ae4ed))

### Features

- **metrics**: Add pure uptime and sla calculations
  ([`99169a5`](https://github.com/mipt-pp-hackaton/rest_assured/commit/99169a53188a0c5eca7326b197a18faff09523e6))


## v1.0.0 (2026-04-14)

- Initial Release
