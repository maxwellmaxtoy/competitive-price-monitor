\# Competitive Price Monitor



A production-style automated price monitoring system built with Python, Playwright, SQLite, Telegram, and Windows Task Scheduler.



The system automatically scrapes product prices, stores historical pricing data, detects price changes, sends significant-change alerts, handles scraper failures, and records operational health metrics.



\---



\## Features



\- Automated product price scraping with Playwright

\- Multi-page pagination

\- Monitors 100 products per run

\- SQLite price history

\- Current vs previous price comparison

\- Configurable percentage alert threshold

\- Telegram price alerts

\- Minor-change filtering

\- Retry and timeout handling

\- Partial scraper failure handling

\- Structured run-history auditing

\- Production health reporting

\- TEST and PRODUCTION environment isolation

\- TEST-mode Telegram suppression

\- Scheduled execution using Windows Task Scheduler

\- Automatic log files

\- Exit-code propagation for scheduler monitoring



\---



\## Tech Stack



\- Python

\- Playwright

\- SQLite

\- JSON configuration

\- Telegram Bot API

\- Windows Task Scheduler

\- Windows Batch Scripts



\---



\## Architecture



```text

Windows Task Scheduler

&#x20;       |

&#x20;       v

run\_monitor.bat

&#x20;       |

&#x20;       v

Python Virtual Environment

&#x20;       |

&#x20;       v

price\_monitor.py

&#x20;       |

&#x20;       +----------------------+

&#x20;       |                      |

&#x20;       v                      v

Playwright Scraper         config.json

&#x20;       |

&#x20;       v

Pagination

&#x20;       |

&#x20;       v

Product Prices

&#x20;       |

&#x20;       v

SQLite

&#x20;       |

&#x20;       +----------------------+

&#x20;       |                      |

&#x20;       v                      v

price\_history            run\_history

&#x20;       |

&#x20;       v

Price Comparison

&#x20;       |

&#x20;       v

Threshold Detection

&#x20;       |

&#x20;       v

Telegram Alerts

