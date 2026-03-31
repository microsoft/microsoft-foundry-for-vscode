# Code Review Checklist

## Correctness
- [ ] Logic is correct and handles edge cases
- [ ] Error handling is present and appropriate
- [ ] Return values and types are consistent

## Security
- [ ] No hardcoded secrets or credentials
- [ ] Input is validated and sanitized
- [ ] No SQL injection, XSS, or command injection vectors

## Performance
- [ ] No unnecessary loops or redundant computations
- [ ] Database queries are efficient (no N+1 issues)
- [ ] Large data sets are paginated or streamed

## Maintainability
- [ ] Code is readable and self-documenting
- [ ] Functions are focused and reasonably sized
- [ ] No dead code or unused imports
