# 🤝 Contributing to PortWatch

Thank you for your interest in contributing to PortWatch! We welcome contributions from developers, OSINT researchers, maritime experts, and data analysts. Your efforts help make advanced vessel risk intelligence accessible to everyone.

Please take a moment to review this document to understand our development workflow, guidelines, and standards.

---

## 📜 Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free community. By participating in this project, you agree to treat all contributors with respect, professional integrity, and constructive cooperation.

---

## 🛠️ How Can I Contribute?

### 1. 🐛 Reporting Bugs
*   Ensure the bug is reproducible under current system configurations.
*   Search open issues to make sure the bug hasn't already been reported.
*   File an issue containing:
    *   Steps to reproduce the error.
    *   System details (OS version, Python version, Node version).
    *   Expected vs. actual behavior.
    *   Stack trace or terminal output snippets.

### 2. 💡 Feature Suggestions
*   Suggest enhancements, including specific geospatial risk indicators, database caching policies, or UI widgets.
*   Open an issue or start a GitHub Discussion describing:
    *   The problem the feature resolves.
    *   The proposed UI or architectural behavior.
    *   Any specific data APIs (e.g. new public registries) utilized.

### 3. ⌨️ Code Submissions (Pull Requests)
*   Fork the repository and create a descriptive feature branch (e.g. `feat/ais-spoofing-algorithm` or `fix/leaflet-marker-rotation`).
*   Ensure all new and modified code includes unit tests and complies with style guides.
*   Submit a Pull Request targeting the `main` or `master` branch.

---

## 💻 Local Development Setup

To establish a complete development environment on your machine:

### 1. Database Setup
PortWatch requires a PostgreSQL instance outfitted with **TimescaleDB** and **PostGIS**. We highly recommend using the official Docker image:
```bash
docker run -d --name portwatch-db -p 5432:5432 \
  -e POSTGRES_DB=portwatch \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  timescale/timescaledb:latest-pg16
```

### 2. Backend Setup
1.  Navigate into `backend/`.
2.  Create and trigger a Python virtual environment (Python >= 3.12):
    ```bash
    python -m venv venv
    source venv/bin/activate # or .\venv\Scripts\activate on Windows
    ```
3.  Install standard and development dependencies in editable mode:
    ```bash
    pip install -e .[dev] || pip install -e .
    ```
4.  Run migrations:
    ```bash
    alembic upgrade head
    ```
5.  Launch API server:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```

### 3. Frontend Setup
1.  Navigate into `frontend/`.
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Launch the Vite React dev server:
    ```bash
    npm run dev
    ```

---

## 🧪 Testing & Linting Standards

### Backend (Python)
*   **Linting:** We strictly enforce linting and syntactic validity. Compile checking can be verified via:
    ```bash
    python -m py_compile $(find app -name "*.py")
    ```
*   **Testing:** We use `pytest` for async endpoint and agent behavior verification.
    ```bash
    pytest
    ```

### Frontend (TypeScript / React)
*   **Build Compilation:** Ensure your changes do not introduce build/TypeScript errors:
    ```bash
    npm run build
    ```

---

## 📝 Git Commit Guidelines

We encourage the use of **Conventional Commits** for clean and automated changelog generation:

*   `feat: add ship-to-ship detection logic`
*   `fix: resolve leaflet rendering error on safari`
*   `docs: update API endpoints for report downloads`
*   `style: refresh glassmorphism effects on vessel search`
*   `refactor: optimize networkx beneficial owner search`

---

## 🚀 Pull Request Checklist

Before submitting a Pull Request, verify that your submission adheres to the following:
- [ ] Code compiles and builds cleanly without warnings or errors.
- [ ] Appropriate unit tests are added or updated.
- [ ] Comments and docstrings are added/preserved for public methods.
- [ ] No temporary configuration edits or credentials are committed.
- [ ] The PR template is filled out completely, referencing any related issues.

---

⚓ **PortWatch Team** — *Thanks again for helping build the premier open-source maritime OSINT platform!*
