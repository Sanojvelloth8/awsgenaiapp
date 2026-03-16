# Non-Functional Requirements Checklist

## Performance
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-P01 | API response time | P95 < 2 seconds | H |
| NFR-P02 | Page load time | < 3 seconds | H |
| NFR-P03 | Database query time | P99 < 500ms | M |
| NFR-P04 | Throughput | 100 req/sec sustained | M |
| NFR-P05 | Batch processing | 10,000 records/hour | L |

## Scalability
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-S01 | Horizontal scaling | Auto-scale 1-10 instances | H |
| NFR-S02 | Peak load handling | 10x normal load for 1 hour | H |
| NFR-S03 | Data growth | Support 1TB data growth/year | M |
| NFR-S04 | User growth | Support 10x user growth | M |

## Availability & Reliability
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-A01 | Uptime SLA | 99.9% (8.7 hrs/year downtime) | H |
| NFR-A02 | Recovery Time Objective | RTO < 4 hours | H |
| NFR-A03 | Recovery Point Objective | RPO < 24 hours | H |
| NFR-A04 | Multi-AZ deployment | No single point of failure | H |
| NFR-A05 | Graceful degradation | Core features available during partial outage | M |

## Security
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-SEC01 | Authentication | MFA supported | H |
| NFR-SEC02 | Authorisation | RBAC with least privilege | H |
| NFR-SEC03 | Data encryption at rest | AES-256 | H |
| NFR-SEC04 | Data encryption in transit | TLS 1.2+ | H |
| NFR-SEC05 | Secret management | No hardcoded secrets | H |
| NFR-SEC06 | Vulnerability scanning | Container images scanned on push | M |
| NFR-SEC07 | Audit logging | All access/change events logged | H |
| NFR-SEC08 | Penetration testing | Annual pen test | M |

## Observability
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-O01 | Structured logging | JSON logs with correlation IDs | H |
| NFR-O02 | Metrics | Key business + system metrics in CloudWatch | H |
| NFR-O03 | Distributed tracing | X-Ray or OTEL tracing | M |
| NFR-O04 | Alerting | PagerDuty/SNS alerts for P1 issues | H |
| NFR-O05 | Dashboards | Operational dashboard for on-call | M |
| NFR-O06 | Log retention | 90 days minimum | M |

## Compliance & Data
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-C01 | Data residency | Data stored in [region] only | H |
| NFR-C02 | GDPR compliance | Right to erasure implemented | H |
| NFR-C03 | Data classification | PII identified and protected | H |
| NFR-C04 | Backup | Daily automated backups | H |
| NFR-C05 | Data retention | 7-year retention for financial data | M |

## Maintainability
| ID    | Requirement | Metric | Priority |
|-------|-------------|--------|----------|
| NFR-M01 | Deployment frequency | Deploy at least weekly | M |
| NFR-M02 | Deployment time | Full deploy < 20 minutes | M |
| NFR-M03 | Test coverage | > 80% unit test coverage | M |
| NFR-M04 | Zero-downtime deployment | Rolling updates, no maintenance window | H |
| NFR-M05 | Rollback capability | Rollback in < 5 minutes | H |
| NFR-M06 | Documentation | All APIs documented with OpenAPI | M |
