import sqlite3

def add_test_movie():
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    # Добавляем тестовый фильм
    test_code = "123"
    test_file_id = "BAACAgIAAxkBAAIBOWgAAXUKvV7kAAE5AAH5AAH5AAH5AAH5AAH5"  # Нужно получить реальный!
    test_caption = "Тестовый фильм #123"
    
    cursor.execute('INSERT OR REPLACE INTO movies VALUES (?, ?, ?)', 
                  (test_code, test_file_id, test_caption))
    conn.commit()
    conn.close()
    
    print(f"✅ Тестовый фильм #{test_code} добавлен!")

if __name__ == "__main__":
    add_test_movie()