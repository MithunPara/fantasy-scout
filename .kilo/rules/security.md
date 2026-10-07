# Security

- Never read or edit anything in `.gitignore`
- Never read or expose `.env` files or credentials
- Never display or include `.env` content in any response
- Never open large data files unrelated to current task
- Never hardcode credentials, API keys, or URLs
- All secrets via environment variables and `python-dotenv`
- Never log tokens, keys, or connection strings
