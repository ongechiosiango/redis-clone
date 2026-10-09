# Contributing to Redis Clone

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment:

   python3 -m venv venv
   source venv/bin/activate

3. Install dependencies:

   pip install -r requirements.txt

## Development Workflow

1. Create a feature branch:

   git checkout -b feature/my-new-feature

2. Make your changes and add tests.
3. Run the test suite:

   pytest

4. Commit your changes with a clear message.
5. Push to your fork and open a Pull Request.

## Coding Standards

- Follow PEP 8.
- Add docstrings to all public functions and classes.
- Include unit tests for new functionality.
- Server code must never block the event loop.

## Reporting Bugs

Open an issue with:

- Your OS and Python version.
- Steps to reproduce.
- Expected vs actual behavior.

## Code of Conduct

Be respectful. We're all here to learn and build.
