# CHANGELOG

<!-- version list -->

## v1.12.3 (2026-05-23)

### Bug Fixes

- Replace python-jose with
  ([`d7a9538`](https://github.com/mipt-pp-hackaton/rest_assured/commit/d7a9538b5a08849b943c792f861aa95b47582859))


## v1.12.2 (2026-05-23)

### Bug Fixes

- Trigger docker release
  ([`38b8ae9`](https://github.com/mipt-pp-hackaton/rest_assured/commit/38b8ae963f10b7b3556056bfb76b9f455ae6a56e))


## v1.12.1 (2026-05-21)

### Bug Fixes

- Structure
  ([`9b29e18`](https://github.com/mipt-pp-hackaton/rest_assured/commit/9b29e18bec52274a72d59829f6ec266e4c593d96))

### Chores

- Auto format
  ([`988b8bd`](https://github.com/mipt-pp-hackaton/rest_assured/commit/988b8bd61b1172e0f85e7b59e195152c2ce76a1e))

- Deleted unneccecary config files
  ([`5f017ae`](https://github.com/mipt-pp-hackaton/rest_assured/commit/5f017ae9842f1c2156af244229b9897becbaca84))

### Refactoring

- Remove test service and related files
  ([`a595f60`](https://github.com/mipt-pp-hackaton/rest_assured/commit/a595f609191fb372a5717f3d50e01facc9ee74c9))

- Replace get_session with session_scope for better session management and add new repository
  functions for incident and service handling
  ([`ace7878`](https://github.com/mipt-pp-hackaton/rest_assured/commit/ace7878c0dc146b2e00fb2cfe30b5ce935aefa8e))

- Tests
  ([`a5b906f`](https://github.com/mipt-pp-hackaton/rest_assured/commit/a5b906f2752516ea8a988b0bff3512e2c69739e6))


## v1.12.0 (2026-05-19)

### Features

- **metrics**: Add metrics service and endpoints
  ([`f90fb9c`](https://github.com/mipt-pp-hackaton/rest_assured/commit/f90fb9c79cdf332fdc94338465481aaff03a555c))

### Refactoring

- Layer logic
  ([`9ae613f`](https://github.com/mipt-pp-hackaton/rest_assured/commit/9ae613fd547b7f4bf16050172aaa4350db9a5636))


## v1.11.0 (2026-05-19)

### Features

- **T1.10**: Add seed script and Makefile target
  ([`418974f`](https://github.com/mipt-pp-hackaton/rest_assured/commit/418974f2cdcf8eef1bd1fc1c1ea77e787af4e618))


## v1.10.0 (2026-05-19)

### Bug Fixes

- **T1.9**: Update listener test payload to JSON format
  ([`645eeef`](https://github.com/mipt-pp-hackaton/rest_assured/commit/645eeefb446e18b8d6d8d9d4e06df33f6b292080))

### Features

- **T1.9**: Add CRUD /api/services with NOTIFY service_changed
  ([`994dbb2`](https://github.com/mipt-pp-hackaton/rest_assured/commit/994dbb2fd54ab3fd252d90dc9897ccc7bd14cdf9))


## v1.9.0 (2026-05-19)

### Bug Fixes

- Lint
  ([`725ce6f`](https://github.com/mipt-pp-hackaton/rest_assured/commit/725ce6f2bdc8a76268c0f5a12a76084e5e0ecdf1))

- **T1.8**: Deduplicate JWT env vars, align field names with JWTConfig
  ([`7928140`](https://github.com/mipt-pp-hackaton/rest_assured/commit/79281401f97424701752edd5321dc35f1e8a62bd))

### Features

- **T1.8**: Implement JWT auth (passwords, jwt, /api/auth/login, get_current_user)
  ([`718ed87`](https://github.com/mipt-pp-hackaton/rest_assured/commit/718ed871d67fa73e6fe852b1fe8062fcc973e629))

### Refactoring

- Layered logic
  ([`f3788a6`](https://github.com/mipt-pp-hackaton/rest_assured/commit/f3788a6d19b4175da0d1430ed67f9b5dca2e8cb2))

- Move auth logic to services and clean up unused files
  ([`10cc304`](https://github.com/mipt-pp-hackaton/rest_assured/commit/10cc304b65346df696be3857191372a20c8c9370))

- Restore authentication logic in services module
  ([`5d5b7dd`](https://github.com/mipt-pp-hackaton/rest_assured/commit/5d5b7dd8a900960c499e56603b82869f009542b4))


## v1.8.0 (2026-05-19)

### Features

- **T1.7**: Add Service (Create/Update/Read) and Token schemas
  ([`c5d9e61`](https://github.com/mipt-pp-hackaton/rest_assured/commit/c5d9e61b8ebc1785c2a223fc926a830d5b903d04))


## v1.7.0 (2026-05-19)

### Bug Fixes

- Migrations
  ([`394d47c`](https://github.com/mipt-pp-hackaton/rest_assured/commit/394d47cfce194205df04995eca9b271f88140368))

- Module importsa
  ([`c727b50`](https://github.com/mipt-pp-hackaton/rest_assured/commit/c727b5002a3b5c591ce1717cf49d6f13130a0fe0))

### Chores

- Auto format
  ([`014351d`](https://github.com/mipt-pp-hackaton/rest_assured/commit/014351d3709252551e2d64b656ef3dd51ee69f45))

### Refactoring

- Layering
  ([`4d0e885`](https://github.com/mipt-pp-hackaton/rest_assured/commit/4d0e8858cb53026ec715a53a89dfbec45792534d))


## v1.6.0 (2026-05-18)

### Bug Fixes

- Apply lint fixes
  ([`7a74298`](https://github.com/mipt-pp-hackaton/rest_assured/commit/7a74298d3ae927601294ae2838f95850caa4f414))

- Replace MetricsService with direct compute_sla call in incidents.py
  ([`c727a82`](https://github.com/mipt-pp-hackaton/rest_assured/commit/c727a82e0eef3b6fe0e6d0767b568f5f23cb87cb))

- Update handle_check_result session handling and fix CI test failures
  ([`48e9cd6`](https://github.com/mipt-pp-hackaton/rest_assured/commit/48e9cd6c6a7f3b82f87d5658b37e642d96de0c6b))

### Chores

- Auto format
  ([`baf94c2`](https://github.com/mipt-pp-hackaton/rest_assured/commit/baf94c2b4365fe72fd98e5c29f32ed69171ed138))

- Update Dockerfile to use settings.toml.example as the default configuration file
  ([`e9c190c`](https://github.com/mipt-pp-hackaton/rest_assured/commit/e9c190cdc9aa8c75934e6b2f33b18065042076ea))

### Code Style

- Fix linter warnings in T4.5 files
  ([`d8fc2a6`](https://github.com/mipt-pp-hackaton/rest_assured/commit/d8fc2a60ab00097f2a92c42dbff741475637a536))

### Features

- **incidents**: Add state machine for incident management with notifications
  ([`dc0b28a`](https://github.com/mipt-pp-hackaton/rest_assured/commit/dc0b28a747ac87c114321575b3d42c0dae2f0d6a))

- **sla**: Add SLA-breach trigger with dedup and tests
  ([`27f8f0b`](https://github.com/mipt-pp-hackaton/rest_assured/commit/27f8f0bc4ebb07183637ba06150c6262d9b3d524))

- **sla**: Add SLA-breach trigger with dedup and tests
  ([`c2941c8`](https://github.com/mipt-pp-hackaton/rest_assured/commit/c2941c8198560cc1459d51aaf7ac400701356183))


## v1.5.0 (2026-05-16)

### Chores

- Prefix Makefile commands with poetry run to ensure execution within virtual environment
  ([`018f069`](https://github.com/mipt-pp-hackaton/rest_assured/commit/018f0699fed1442ceb3406083705586e3c567e97))

### Continuous Integration

- Add container publishing
  ([`445876b`](https://github.com/mipt-pp-hackaton/rest_assured/commit/445876b44dbf9c0062e025ea1f3fcdf796419925))

### Features

- Add service model check constraints and update migration versioning
  ([`eac688b`](https://github.com/mipt-pp-hackaton/rest_assured/commit/eac688b3184caba6d0e2acd665fa952a362018f2))

### Refactoring

- Improve import sorting and formatting for service model database constraints
  ([`41dd793`](https://github.com/mipt-pp-hackaton/rest_assured/commit/41dd793141393a226b1634b5b229e9297106b6c0))


## v1.4.0 (2026-05-16)

### Chores

- Auto format
  ([`2b120f7`](https://github.com/mipt-pp-hackaton/rest_assured/commit/2b120f79efe8341454aa6605faf903f6db437715))

- Remove obsolete settings.toml bootstrapping from CI and add flint target to Makefile
  ([`6b213fc`](https://github.com/mipt-pp-hackaton/rest_assured/commit/6b213fcd2696ded71ce794e2b1481255fd351369))

- Track settings.toml in version control and remove example template
  ([`6002649`](https://github.com/mipt-pp-hackaton/rest_assured/commit/6002649a4c5393cf92519f85ebd91980a496001a))

### Continuous Integration

- Added mailhog
  ([`b244c57`](https://github.com/mipt-pp-hackaton/rest_assured/commit/b244c57aad4a0542179bc03c29ae698752effbb5))

### Features

- Implement incident and notification log models with related migrations and integration tests
  ([`d307195`](https://github.com/mipt-pp-hackaton/rest_assured/commit/d307195b15e1f0c1ff05f5dccbb81e01461fe77e))

- Implement incident and notification models with associated database migrations and integration
  tests
  ([`7384bc1`](https://github.com/mipt-pp-hackaton/rest_assured/commit/7384bc1f48d07ede7664475f2cac4b92c5ea1930))

- **models**: Add Incident and NotificationLog models with migration and tests
  ([`8898990`](https://github.com/mipt-pp-hackaton/rest_assured/commit/889899069ab5fbacd67402249750254c040127db))

- **notifications**: Add EmailSender with Jinja2 templates and tests
  ([`965a750`](https://github.com/mipt-pp-hackaton/rest_assured/commit/965a7503f83738ebd248384697b507537f12ec08))


## v1.3.0 (2026-05-12)

### Features

- Add smtp and notifications configurations to global Settings and clean up redundant integration
  tests
  ([`816714e`](https://github.com/mipt-pp-hackaton/rest_assured/commit/816714e38a9b8e9b1df94761f4a293cb90bd21da))


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
