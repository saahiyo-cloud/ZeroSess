# 🤝 Contributing to ZeroSess

Thank you for your interest in contributing to ZeroSess!

## How to Contribute

1. **Fork the Repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<your-username>/ZeroSess.git
   cd ZeroSess
   ```
3. **Create a new branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install flake8 black
   ```
5. **Make your changes** and test thoroughly.
6. **Ensure code quality**:
   ```bash
   python -m compileall bot/
   flake8 bot/
   ```
7. **Commit & Push**:
   ```bash
   git commit -m "feat: add support for new feature"
   git push origin feature/my-new-feature
   ```
8. **Open a Pull Request** against the `main` branch.

## Code Standards
- Keep async code clean and non-blocking.
- Never write credentials or sensitive data to disk or logs.
- Adhere to the existing FSM wizard architecture.
