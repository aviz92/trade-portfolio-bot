# PyPI Stats – Useful `pypistats` Commands

A quick reference for the most useful commands to analyze your package usage.

Replace `<package>` with your package name.

---

## 1. Overall Downloads (Most Important)

Shows total downloads including and excluding mirrors.

```bash
pypistats overall <package>
```

**Tip:**
`without_mirrors` ≈ closest estimate to real usage.

### Last month

```bash
pypistats overall <package> --last-month
```

### Last week

```bash
pypistats overall <package> --last-week
```

---

## 2. Download Trend (Growth Over Time)

Daily / weekly download history.

```bash
pypistats recent <package>
```

By period:

```bash
pypistats recent <package> --period day
pypistats recent <package> --period week
pypistats recent <package> --period month
```

Use this to detect:

* Growth
* Release impact
* Traffic spikes

---

## 3. Downloads by Operating System

Helps estimate real users vs CI.

```bash
pypistats system <package>
```

Interpretation:

| Category         | Meaning                     |
| ---------------- | --------------------------- |
| Windows / Darwin | Usually real developers     |
| Linux            | Mixed (servers, Docker, CI) |
| null             | CI / proxies / automation   |

Last month:

```bash
pypistats system <package> --last-month
```

---

## 4. Python Version Usage

See which Python versions your users run.

```bash
pypistats python_minor <package>
```

Or major versions:

```bash
pypistats python_major <package>
```

Useful for:

* Dropping old versions
* Detecting CI (many versions at once)

---

## 5. Package Version Adoption

Which versions of your package are being used.

```bash
pypistats version <package>
```

Useful to:

* Check upgrade adoption
* Identify users stuck on old releases

---

## 6. Mirrors Analysis

Compare downloads with and without mirrors.

```bash
pypistats overall <package> --mirrors
```

---

## 7. JSON Output (for scripts)

```bash
pypistats overall <package> --format json
```

---

## 8. Custom Date Range

```bash
pypistats system <package> --start-date 2026-01-01 --end-date 2026-01-31
```

---

## Recommended Maintainer Dashboard

Run these regularly:

```bash
pypistats overall <package> --last-month
pypistats system <package> --last-month
pypistats python_minor <package> --last-month
pypistats version <package>
pypistats recent <package>
```

---

## Quick Interpretation Cheat Sheet

| Metric                       | What it means               |
| ---------------------------- | --------------------------- |
| without_mirrors              | Best estimate of real usage |
| null (system)                | Mostly CI / automation      |
| Windows + Darwin             | Real developers             |
| Many Python versions         | Likely CI/testing           |
| Old package version dominant | Users not upgrading         |

---

## Web Dashboard

View stats online:

[https://pypistats.org/packages/](https://pypistats.org/packages/)<package>
