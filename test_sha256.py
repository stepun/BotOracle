#!/usr/bin/env python3
import hashlib

# Данные из вашего примера
api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJHR1NlbGxlciIsInN1YiI6MjExLCJpYXQiOjE3NjI2MTA0MzMsImV4cCI6MTc2NTIwMjQzMywianRpIjoiMDU3MWEyOTQtODc0Ni00ZDMwLTljMTItYWY3ZTA3NzRmNGFiIiwidXNlciI6eyJpZCI6MjExLCJlbWFpbCI6ImFyLWZ1dG9yaWdpbkB5YW5kZXgucnUifSwidXVpZCI6ImMyYjY3MzQzLTE2YTItNDkzZC05NjY5LTlkNzc5MGZkMGI5MiJ9.5I2BEb8C5rE3lyhbGY3eY4nh9FO-1shr39FlxkTPT-s"
timestamp = "1762611040094"

# Строка для хеширования
sign_string = api_key + timestamp

print("=" * 80)
print("ТЕСТ SHA256 ПОДПИСИ")
print("=" * 80)
print(f"\nAPI Key: {api_key}")
print(f"\nTimestamp: {timestamp}")
print(f"\nДлина API Key: {len(api_key)}")
print(f"Длина Timestamp: {len(timestamp)}")
print(f"\nСтрока для хеширования (api_key + timestamp):")
print(f"{sign_string}")
print(f"\nДлина строки: {len(sign_string)}")

# Вычисляем SHA256
sha256_hash = hashlib.sha256(sign_string.encode('utf-8')).hexdigest()

print(f"\n" + "=" * 80)
print(f"SHA256 (UTF-8): {sha256_hash}")
print("=" * 80)

print(f"\nОжидаемый результат (онлайн калькулятор):")
print(f"9afb2d3a4ba4cf98f4599e59de30c7bc061897bbd8f3b993fdd4e26c8fb4bc48")

print(f"\nРезультат из JavaScript кода:")
print(f"683e7ca35a870a52e8e989235ea8c3eb38d58fc0694ace5d543b80db8b308d99")

print(f"\nСовпадает с онлайн калькулятором: {sha256_hash == '9afb2d3a4ba4cf98f4599e59de30c7bc061897bbd8f3b993fdd4e26c8fb4bc48'}")

# Попробуем разные варианты
print(f"\n" + "=" * 80)
print("ДРУГИЕ ВАРИАНТЫ:")
print("=" * 80)

# Вариант 1: UTF-16
try:
    sha256_utf16 = hashlib.sha256(sign_string.encode('utf-16')).hexdigest()
    print(f"\nSHA256 (UTF-16): {sha256_utf16}")
except Exception as e:
    print(f"\nОшибка UTF-16: {e}")

# Вариант 2: UTF-16LE
try:
    sha256_utf16le = hashlib.sha256(sign_string.encode('utf-16le')).hexdigest()
    print(f"SHA256 (UTF-16LE): {sha256_utf16le}")
except Exception as e:
    print(f"Ошибка UTF-16LE: {e}")

# Вариант 3: UTF-16BE
try:
    sha256_utf16be = hashlib.sha256(sign_string.encode('utf-16be')).hexdigest()
    print(f"SHA256 (UTF-16BE): {sha256_utf16be}")
except Exception as e:
    print(f"Ошибка UTF-16BE: {e}")

# Вариант 4: Latin-1
try:
    sha256_latin1 = hashlib.sha256(sign_string.encode('latin-1')).hexdigest()
    print(f"SHA256 (Latin-1): {sha256_latin1}")
except Exception as e:
    print(f"Ошибка Latin-1: {e}")

# Вариант 5: ASCII
try:
    sha256_ascii = hashlib.sha256(sign_string.encode('ascii')).hexdigest()
    print(f"SHA256 (ASCII): {sha256_ascii}")
except Exception as e:
    print(f"Ошибка ASCII: {e}")

# Проверим побайтово
print(f"\n" + "=" * 80)
print("БАЙТЫ (первые 50 символов):")
print("=" * 80)
print(f"UTF-8: {sign_string[:50].encode('utf-8').hex()}")
