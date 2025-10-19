---
inclusion: always
---
---
inclusion: always
---

## Python Environment

This project uses a virtual environment at `.venv`. All Python commands must run within this environment:

- Windows cmd: `.venv\Scripts\activate & <command>`
- Windows PowerShell: `.venv\Scripts\activate ; <command>`

Examples:
```
.venv\Scripts\activate & python app.py
.venv\Scripts\activate & pip install <package>
.venv\Scripts\activate & pytest tests/
```

After installing packages, update requirements: `.venv\Scripts\activate & pip freeze > requirements.txt`

## Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Handle errors using custom exceptions from `backend/utils/errors.py`
- Use centralized logging from `backend/utils/logging.py` (never use print statements)
- Access configuration via `backend/utils/config.py`, not directly from `config.yaml`
- All agents must inherit from `backend/agents/base.py`
- All plugins should follow the established plugin pattern with proper error handling