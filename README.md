# 🔥 Decouple — Cloud Lock-In Analyzer

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi"/>
  <img src="https://img.shields.io/badge/Focus-Cloud%20Migration-blueviolet?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Intelligence-Lock--In%20Analysis-orange?style=for-the-badge"/>
</p>

---

## 🧠 What is this?

**Decouple** scans any GitHub repo and tells you:

* ☁️ Which cloud providers you're using
* 🔗 How locked-in you are
* 🧩 What services are binding you
* ⚠️ How hard migration will be

> Think: *“What happens if I need to leave this cloud tomorrow?”*

---

## ⚡ Example

```bash
GET /decouple/scan?repo_url=https://github.com/davex-ai/Fire-Auth-Kit
```

### 🔍 Output

```json
{
  "vendors": ["gcp", "firebase"],
  "lock_in_score": 100,
  "services": {
    "firebase": {
      "firebase-auth": 11,
      "firestore": 14,
      "cloud-messaging": 5
    }
  },
  "migration_difficulty": {
    "easy": 1,
    "medium": 2,
    "hard": 4
  }
}
```

---

## 📊 What It Detects

### ☁️ Vendors

* AWS
* GCP
* Firebase
* Azure
* Vercel
* IaC (Terraform, Kubernetes, etc.)

---

### 🔧 Services (Deep Detection)

| Category  | Examples                      |
| --------- | ----------------------------- |
| Auth      | Firebase Auth, IAM            |
| Databases | Firestore, DynamoDB, BigQuery |
| Compute   | Lambda, Cloud Functions       |
| Storage   | S3, GCS                       |
| Infra     | Terraform, Kubernetes         |

---

## 🧬 How It Works

### 1. 📦 Dependency Analysis

* `package.json`
* `requirements.txt`
* `go.mod`, `Cargo.toml`, etc.

---

### 2. 🧠 Import Intelligence

Detects actual usage:

```js
import { initializeApp } from "firebase/app"
```

```python
from google.cloud import storage
```

---

### 3. 🔍 Fuzzy Detection

Finds hidden signals:

* config files
* env vars
* raw SDK usage

---

### 4. ⚖️ Lock-In Scoring

Each service is weighted:

| Type      | Impact                  |
| --------- | ----------------------- |
| 🔴 Hard   | Firestore, DynamoDB     |
| 🟡 Medium | Lambda, Cloud Functions |
| 🟢 Easy   | S3, Docker              |

---

## 🧨 Lock-In Score

```txt
0   → Fully portable
50  → Moderate coupling
100 → Deep vendor lock-in
```

---

## 🚧 Migration Difficulty

```json
{
  "easy": 1,
  "medium": 2,
  "hard": 4
}
```

### Meaning:

* 🟢 Easy → Swap with minimal effort
* 🟡 Medium → Requires refactor
* 🔴 Hard → Full rewrite / redesign

---

## 🛠️ API

### Scan a repo

```bash
GET /decouple/scan?repo_url=<github_url>
```

---

### Debug mode (insane detail)

```bash
GET /decouple/debug?repo_url=<github_url>
```

Includes:

* file-by-file breakdown
* detected imports
* dependency matches
* fuzzy signals

---

## 🧪 Real Use Cases

* 🏢 Companies planning cloud migration
* 💰 Cost optimization audits
* 🔐 Risk assessment (vendor lock-in exposure)
* 🚀 Devs building multi-cloud apps

---

## ⚡ Why This is Different

Most tools:

> "You use AWS"

Decouple:

> "You're using DynamoDB + Lambda → migration = HARD"

---

## 🔮 Roadmap

* [ ] 🔁 Auto migration recommendations
* [ ] 💡 Service alternatives (AWS → GCP mappings)
* [ ] 📊 Web dashboard
* [ ] 🤖 AI-powered architecture breakdown

---

## 👨‍💻 Author

Built by **davex-ai**

> Turning repos into architecture intelligence ⚡

---

## ⭐ Support

If this helped you:

```bash
⭐ Star the repo
🍴 Fork it
🧠 Break it
```

---

<p align="center">
  <b>Understand your stack before it owns you.</b>
</p>
