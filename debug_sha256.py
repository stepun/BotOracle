#!/usr/bin/env python3
import hashlib

# Данные из вашего примера
api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJHR1NlbGxlciIsInN1YiI6MjExLCJpYXQiOjE3NjI2MTA0MzMsImV4cCI6MTc2NTIwMjQzMywianRpIjoiMDU3MWEyOTQtODc0Ni00ZDMwLTljMTItYWY3ZTA3NzRmNGFiIiwidXNlciI6eyJpZCI6MjExLCJlbWFpbCI6ImFyLWZ1dG9yaWdpbkB5YW5kZXgucnUifSwidXVpZCI6ImMyYjY3MzQzLTE2YTItNDkzZC05NjY5LTlkNzc5MGZkMGI5MiJ9.5I2BEb8C5rE3lyhbGY3eY4nh9FO-1shr39FlxkTPT-s"
timestamp = "1762611040094"

target_hash = "683e7ca35a870a52e8e989235ea8c3eb38d58fc0694ace5d543b80db8b308d99"

print("=" * 80)
print("ПОИСК СТРОКИ, КОТОРАЯ ДАЕТ НУЖНЫЙ ХЕШ")
print("=" * 80)
print(f"Целевой хеш: {target_hash}\n")

# Вариант 1: api_key + timestamp
test1 = api_key + timestamp
hash1 = hashlib.sha256(test1.encode('utf-8')).hexdigest()
print(f"1. api_key + timestamp (UTF-8): {hash1}")
if hash1 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 2: timestamp + api_key
test2 = timestamp + api_key
hash2 = hashlib.sha256(test2.encode('utf-8')).hexdigest()
print(f"2. timestamp + api_key (UTF-8): {hash2}")
if hash2 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 3: только api_key
hash3 = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
print(f"3. только api_key (UTF-8): {hash3}")
if hash3 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 4: только timestamp
hash4 = hashlib.sha256(timestamp.encode('utf-8')).hexdigest()
print(f"4. только timestamp (UTF-8): {hash4}")
if hash4 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 5: с пробелом между
test5 = api_key + " " + timestamp
hash5 = hashlib.sha256(test5.encode('utf-8')).hexdigest()
print(f"5. api_key + ' ' + timestamp (UTF-8): {hash5}")
if hash5 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 6: с переносом строки
test6 = api_key + "\n" + timestamp
hash6 = hashlib.sha256(test6.encode('utf-8')).hexdigest()
print(f"6. api_key + '\\n' + timestamp (UTF-8): {hash6}")
if hash6 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 7: UTF-16LE для api_key + timestamp
hash7 = hashlib.sha256(test1.encode('utf-16le')).hexdigest()
print(f"7. api_key + timestamp (UTF-16LE): {hash7}")
if hash7 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 8: UTF-16BE для api_key + timestamp
hash8 = hashlib.sha256(test1.encode('utf-16be')).hexdigest()
print(f"8. api_key + timestamp (UTF-16BE): {hash8}")
if hash8 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 9: Может быть timestamp - это число, а не строка?
test9 = api_key + str(1762611040094)
hash9 = hashlib.sha256(test9.encode('utf-8')).hexdigest()
print(f"9. api_key + число timestamp: {hash9}")
if hash9 == target_hash:
    print("   ✅ НАЙДЕНО!")

# Вариант 10: Попробуем подобрать, хешируя разные части
print("\n" + "=" * 80)
print("ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ:")
print("=" * 80)

# Может проблема в том, что api_key читается из переменной неправильно?
# Попробуем разные варианты api_key
api_key_variants = [
    ("api_key без кавычек", api_key),
    ("'api_key'", f"'{api_key}'"),
    ('"api_key"', f'"{api_key}"'),
]

for name, variant in api_key_variants:
    test = variant + timestamp
    h = hashlib.sha256(test.encode('utf-8')).hexdigest()
    if h == target_hash:
        print(f"✅ НАЙДЕНО! {name} + timestamp")
        print(f"   Строка: {test[:100]}...")
        break

print("\n" + "=" * 80)
print("ИНФОРМАЦИЯ:")
print("=" * 80)
print(f"Пустая строка SHA256: {hashlib.sha256(b'').hexdigest()}")
print(f"Ваш первый результат:  {target_hash}")
print(f"Второй результат был:   e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
