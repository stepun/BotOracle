#!/usr/bin/env python3
import hashlib

# Новый timestamp
api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJHR1NlbGxlciIsInN1YiI6MjExLCJpYXQiOjE3NjI2MTA0MzMsImV4cCI6MTc2NTIwMjQzMywianRpIjoiMDU3MWEyOTQtODc0Ni00ZDMwLTljMTItYWY3ZTA3NzRmNGFiIiwidXNlciI6eyJpZCI6MjExLCJlbWFpbCI6ImFyLWZ1dG9yaWdpbkB5YW5kZXgucnUifSwidXVpZCI6ImMyYjY3MzQzLTE2YTItNDkzZC05NjY5LTlkNzc5MGZkMGI5MiJ9.5I2BEb8C5rE3lyhbGY3eY4nh9FO-1shr39FlxkTPT-s"
timestamp = "1762612228298"

sign_string = api_key + timestamp

print("=" * 80)
print("ТЕСТ НОВОГО TIMESTAMP")
print("=" * 80)
print(f"Timestamp: {timestamp}")
print(f"Строка: {sign_string[:80]}...")
print(f"Длина: {len(sign_string)}")

sha256_hash = hashlib.sha256(sign_string.encode('utf-8')).hexdigest()
print(f"\nПравильный SHA256 (UTF-8):")
print(f"{sha256_hash}")

print(f"\nОнлайн сервис показал:")
print(f"1756f8bf8b5bd5c686bbd1bce3da1733eb2443de75d3b87803155c34493ee72f")

print(f"\nJavaScript код выдал:")
print(f"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

# Проверим - это хеш пустой строки?
empty_hash = hashlib.sha256(b'').hexdigest()
print(f"\nSHA256 пустой строки:")
print(f"{empty_hash}")
print(f"Совпадает с JS кодом: {empty_hash == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}")
