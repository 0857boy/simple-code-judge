import os
import subprocess
import tempfile
import time
import logging
import json
import zipfile
import io
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('judge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 設定
class Config:
    TESTCASE_DIR = "/app/testcases"
    CONFIG_FILE = "/app/testcases/config.json"
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    SUPPORTED_LANGUAGES = ["cpp", "java", "python", "javascript", "golang"]

# 預設設定值
DEFAULT_SETTINGS = {
    "execution_time_limit": 5,  # 秒
    "memory_limit": 128,  # MB
    "compile_time_limit": 10,  # 秒
    "auto_save_code": True,  # 自動保存程式碼
    "show_execution_time": True,  # 顯示執行時間
}

app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE

# 確保目錄存在
os.makedirs(Config.TESTCASE_DIR, exist_ok=True)

# 語言編譯和執行配置
LANGUAGE_CONFIG = {
    "cpp": {
        "extension": ".cpp",
        "compile_cmd": ["g++", "-std=c++17", "-O2", "-o", "main", "main.cpp"],
        "run_cmd": ["./main"],
        "need_compile": True
    },
    "java": {
        "extension": ".java",
        "compile_cmd": ["javac", "Main.java"],
        "run_cmd": ["java", "Main"],
        "need_compile": True
    },
    "python": {
        "extension": ".py",
        "compile_cmd": [],
        "run_cmd": ["python3", "main.py"],
        "need_compile": False
    },
    "javascript": {
        "extension": ".js",
        "compile_cmd": [],
        "run_cmd": ["node", "main.js"],
        "need_compile": False
    },
    "golang": {
        "extension": ".go",
        "compile_cmd": ["go", "build", "-o", "main", "main.go"],
        "run_cmd": ["./main"],
        "need_compile": True
    }
}

def load_config() -> Dict:
    """載入配置檔案"""
    try:
        if os.path.exists(Config.CONFIG_FILE):
            with open(Config.CONFIG_FILE, "r", encoding='utf-8') as f:
                config = json.load(f)
                # 確保所有預設設定都存在
                if "settings" not in config:
                    config["settings"] = DEFAULT_SETTINGS.copy()
                else:
                    # 合併預設設定，確保新增的設定項目有預設值
                    for key, value in DEFAULT_SETTINGS.items():
                        if key not in config["settings"]:
                            config["settings"][key] = value
                return config
    except Exception as e:
        logger.error(f"載入配置檔案失敗: {e}")
    return {"last_lang": "", "statistics": {}, "settings": DEFAULT_SETTINGS.copy()}

def save_config(config: Dict) -> None:
    """儲存配置檔案"""
    try:
        with open(Config.CONFIG_FILE, "w", encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"儲存配置檔案失敗: {e}")

def get_setting(key: str, default=None):
    """獲取單個設定值"""
    config = load_config()
    return config.get("settings", {}).get(key, default or DEFAULT_SETTINGS.get(key))

def update_setting(key: str, value):
    """更新單個設定值"""
    config = load_config()
    if "settings" not in config:
        config["settings"] = DEFAULT_SETTINGS.copy()
    config["settings"][key] = value
    save_config(config)

def validate_testcase_name(name: str) -> bool:
    """驗證測試案例名稱的有效性"""
    if not name or len(name) > 50:
        return False
    # 只允許字母、數字、底線、連字號
    return all(c.isalnum() or c in '_-' for c in name)

def sanitize_output(output: str) -> str:
    """清理輸出內容"""
    return output

def get_testcase_stats() -> Dict:
    """獲取測試案例統計資訊"""
    try:
        files = os.listdir(Config.TESTCASE_DIR)
        in_files = [f for f in files if f.endswith('.in')]
        out_files = [f for f in files if f.endswith('.out')]
        
        testcases = set()
        for f in in_files:
            testcases.add(f[:-3])  # 移除 .in
            
        return {
            "total_testcases": len(testcases),
            "in_files": len(in_files),
            "out_files": len(out_files),
            "last_modified": datetime.fromtimestamp(
                max([os.path.getmtime(os.path.join(Config.TESTCASE_DIR, f)) 
                     for f in files] or [0])
            ).isoformat() if files else None
        }
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {e}")
        return {"total_testcases": 0, "in_files": 0, "out_files": 0}

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "檔案過大，請上傳小於16MB的檔案"}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"內部伺服器錯誤: {e}")
    return jsonify({"error": "內部伺服器錯誤，請稍後再試"}), 500

@app.route("/")
def home():
    return send_file('index.html')

@app.route('/favicons_io/<path:filename>')
def static_files(filename):
    return send_from_directory('favicons_io', filename)

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """獲取系統統計資訊"""
    try:
        stats = get_testcase_stats()
        config = load_config()
        
        return jsonify({
            "testcase_stats": stats,
            "last_language": config.get("last_lang", ""),
            "supported_languages": Config.SUPPORTED_LANGUAGES,
            "max_execution_time": get_setting("execution_time_limit"),
            "memory_limit": get_setting("memory_limit"),
            "compile_time_limit": get_setting("compile_time_limit")
        }), 200
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {e}")
        return jsonify({"error": "獲取統計資訊失敗"}), 500

@app.route("/upload", methods=["POST"])
def upload_testcase():
    """上傳測試資料"""
    try:
        name = request.form.get("name", "").strip()
        test_input = request.form.get("input", "")
        test_output = request.form.get("output", "")

        if not name or not test_input:
            return jsonify({"error": "請提供測試檔名和輸入內容"}), 400

        if not validate_testcase_name(name):
            return jsonify({"error": "測試檔名無效，只能包含字母、數字、底線和連字號，長度不超過50字符"}), 400

        input_filename = f"{name}.in"
        output_filename = f"{name}.out"

        # 使用安全的檔案名
        safe_input_filename = secure_filename(input_filename)
        safe_output_filename = secure_filename(output_filename)

        input_path = os.path.join(Config.TESTCASE_DIR, safe_input_filename)
        output_path = os.path.join(Config.TESTCASE_DIR, safe_output_filename)

        with open(input_path, "w", encoding='utf-8') as f:
            f.write(test_input)

        if test_output:
            with open(output_path, "w", encoding='utf-8') as f:
                f.write(test_output)

        logger.info(f"上傳測試資料: {name}")
        return jsonify({"message": f"{name} 測試資料上傳成功"}), 200

    except Exception as e:
        logger.error(f"上傳測試資料失敗: {e}")
        return jsonify({"error": "上傳失敗，請稍後再試"}), 500

@app.route("/testcases", methods=["GET"])
def list_testcases():
    """列出測試資料"""
    try:
        files = os.listdir(Config.TESTCASE_DIR)
        # 過濾出有效的測試檔案
        valid_files = [f for f in files if f.endswith(('.in', '.out')) and 
                      os.path.isfile(os.path.join(Config.TESTCASE_DIR, f))]
        return jsonify(valid_files), 200
    except Exception as e:
        logger.error(f"列出測試資料失敗: {e}")
        return jsonify({"error": "無法獲取測試資料列表"}), 500

@app.route("/testcases/<name>", methods=["GET"])
def get_testcase(name):
    """獲取特定測試資料"""
    try:
        if not validate_testcase_name(name):
            return jsonify({"error": "無效的測試檔名"}), 400

        safe_name = secure_filename(name)
        input_filename = os.path.join(Config.TESTCASE_DIR, f"{safe_name}.in")
        output_filename = os.path.join(Config.TESTCASE_DIR, f"{safe_name}.out")

        if not os.path.exists(input_filename):
            return jsonify({"error": "測試資料不存在"}), 404

        with open(input_filename, "r", encoding='utf-8') as f:
            test_input = f.read()

        test_output = ""
        if os.path.exists(output_filename):
            with open(output_filename, "r", encoding='utf-8') as f:
                test_output = f.read()

        return jsonify({
            "input": test_input, 
            "output": test_output,
            "has_output": os.path.exists(output_filename)
        }), 200

    except Exception as e:
        logger.error(f"獲取測試資料失敗: {e}")
        return jsonify({"error": "獲取測試資料失敗"}), 500

@app.route("/export", methods=["GET"])
def export_testcases():
    """匯出測試資料"""
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(Config.TESTCASE_DIR):
                for file in files:
                    if file.endswith(('.in', '.out')):
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, Config.TESTCASE_DIR))
        
        memory_file.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"testcases_{timestamp}.zip"
        
        logger.info("匯出測試資料")
        return send_file(memory_file, as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f"匯出測試資料失敗: {e}")
        return jsonify({"error": "匯出失敗"}), 500

@app.route("/import", methods=["POST"])
def import_testcases():
    """匯入測試資料"""
    try:
        imported_count = 0
        
        # 處理 ZIP 檔案
        if 'zipfile' in request.files:
            zip_file = request.files['zipfile']
            if zip_file and zip_file.filename and zip_file.filename.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(zip_file.stream, 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            if not file_info.is_dir() and file_info.filename.endswith(('.in', '.out')):
                                # 取得檔案名稱
                                filename = os.path.basename(file_info.filename)
                                base_name = filename.rsplit('.', 1)[0]
                                
                                if validate_testcase_name(base_name):
                                    file_path = os.path.join(Config.TESTCASE_DIR, filename)
                                    with zip_ref.open(file_info) as source_file:
                                        with open(file_path, 'wb') as target_file:
                                            target_file.write(source_file.read())
                                    imported_count += 1
                except Exception as e:
                    logger.error(f"解壓縮 ZIP 檔案失敗: {e}")
                    return jsonify({"error": "ZIP 檔案格式錯誤或無法解壓縮"}), 400
        
        # 處理單個檔案
        if 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(os.path.basename(file.filename))
                    if filename.endswith(('.in', '.out')):
                        # 驗證檔案名
                        base_name = filename.rsplit('.', 1)[0]
                        if validate_testcase_name(base_name):
                            file_path = os.path.join(Config.TESTCASE_DIR, filename)
                            file.save(file_path)
                            imported_count += 1

        if imported_count == 0:
            return jsonify({"error": "沒有有效的測試檔案可匯入"}), 400

        logger.info(f"匯入 {imported_count} 個測試檔案")
        return jsonify({"message": f"成功匯入 {imported_count} 個測試檔案"}), 200

    except Exception as e:
        logger.error(f"匯入測試資料失敗: {e}")
        return jsonify({"error": "匯入失敗"}), 500

@app.route("/delete", methods=["POST"])
def delete_testcases():
    """刪除測試資料"""
    try:
        data = request.get_json()
        if not data or 'testcases' not in data:
            return jsonify({"error": "請提供要刪除的測試資料"}), 400

        testcases = data.get("testcases", [])
        if not testcases:
            return jsonify({"error": "請提供要刪除的測試資料"}), 400

        deleted_count = 0
        for testcase in testcases:
            if validate_testcase_name(testcase):
                safe_name = secure_filename(testcase)
                input_file = os.path.join(Config.TESTCASE_DIR, safe_name + ".in")
                output_file = os.path.join(Config.TESTCASE_DIR, safe_name + ".out")
                
                if os.path.exists(input_file):
                    os.remove(input_file)
                    deleted_count += 1
                if os.path.exists(output_file):
                    os.remove(output_file)

        logger.info(f"刪除 {deleted_count} 個測試檔案")
        return jsonify({"message": f"成功刪除 {deleted_count} 個測試檔案"}), 200

    except Exception as e:
        logger.error(f"刪除測試資料失敗: {e}")
        return jsonify({"error": "刪除失敗"}), 500

@app.route("/deleteAll", methods=["POST"])
def delete_all_testcases():
    """刪除所有測試資料"""
    try:
        files = os.listdir(Config.TESTCASE_DIR)
        deleted_count = 0
        
        for file in files:
            if file.endswith(('.in', '.out')):
                file_path = os.path.join(Config.TESTCASE_DIR, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1

        logger.info(f"刪除所有測試資料，共 {deleted_count} 個檔案")
        return jsonify({"message": f"成功刪除所有測試資料 ({deleted_count} 個檔案)"}), 200

    except Exception as e:
        logger.error(f"刪除所有測試資料失敗: {e}")
        return jsonify({"error": "刪除失敗"}), 500

def compile_and_run_code(code: str, lang: str, input_data: str, temp_dir: str) -> Tuple[str, bool, str]:
    """編譯並執行程式碼"""
    try:
        config = LANGUAGE_CONFIG.get(lang)
        if not config:
            return "不支援的程式語言", False, ""

        # 準備程式碼檔案
        if lang == "java":
            code_file = os.path.join(temp_dir, "Main.java")
        else:
            code_file = os.path.join(temp_dir, f"main{config['extension']}")

        with open(code_file, "w", encoding='utf-8') as f:
            f.write(code)

        # 編譯 (如果需要)
        if config['need_compile']:
            try:
                compile_result = subprocess.run(
                    config['compile_cmd'], 
                    cwd=temp_dir,
                    capture_output=True, 
                    text=True, 
                    timeout=get_setting("compile_time_limit")
                )
                if compile_result.returncode != 0:
                    return f"編譯錯誤: {compile_result.stderr}", False, ""
            except subprocess.TimeoutExpired:
                return "編譯時間過長", False, ""

        # 執行程式
        try:
            start_time = time.time()
            result = subprocess.run(
                config['run_cmd'],
                input=input_data,
                cwd=temp_dir,
                text=True,
                capture_output=True,
                timeout=get_setting("execution_time_limit")
            )
            execution_time = time.time() - start_time

            user_output = sanitize_output(result.stdout)
            
            if result.returncode != 0:
                error_msg = sanitize_output(result.stderr)
                return f"{user_output}\n執行錯誤: {error_msg}", False, f"{execution_time:.3f}s"
            
            return user_output, True, f"{execution_time:.3f}s"

        except subprocess.TimeoutExpired:
            return f"執行時間過長 (超過{get_setting('execution_time_limit')}秒)", False, f">{get_setting('execution_time_limit')}s"

    except Exception as e:
        logger.error(f"執行程式碼失敗: {e}")
        return f"執行錯誤: {str(e)}", False, ""

@app.route("/judge", methods=["POST"])
def judge_code():
    """評判程式碼"""
    try:
        code = request.form.get("code", "").strip()
        lang = request.form.get("lang", "").strip()

        if not code:
            return jsonify({"error": "請提供程式碼"}), 400

        if lang not in Config.SUPPORTED_LANGUAGES and lang != "default":
            return jsonify({"error": f"不支援的程式語言。支援的語言: {', '.join(Config.SUPPORTED_LANGUAGES)}"}), 400

        # 處理預設語言
        config = load_config()
        if lang == "default":
            if not config.get("last_lang"):
                return jsonify({"error": "目前沒有預設語言，請先選擇一種語言"}), 400
            lang = config["last_lang"]
        else:
            config["last_lang"] = lang
            save_config(config)

        # 獲取測試資料
        try:
            inputs = sorted([f for f in os.listdir(Config.TESTCASE_DIR) if f.endswith(".in")])
        except Exception:
            inputs = []

        if not inputs:
            return jsonify({"error": "沒有可用的測試資料"}), 400

        results = {}
        success_count = 0

        # 使用臨時目錄執行程式碼
        with tempfile.TemporaryDirectory() as temp_dir:
            for input_file in inputs:
                output_file = input_file.replace(".in", ".out")
                input_path = os.path.join(Config.TESTCASE_DIR, input_file)
                output_path = os.path.join(Config.TESTCASE_DIR, output_file)

                try:
                    # 讀取輸入資料
                    with open(input_path, "r", encoding='utf-8') as f:
                        input_data = f.read()

                    # 執行程式碼
                    user_output, success, exec_time = compile_and_run_code(code, lang, input_data, temp_dir)
                    
                    # 讀取預期輸出
                    expected_output = ""
                    has_expected = os.path.exists(output_path)
                    if has_expected:
                        with open(output_path, "r", encoding='utf-8') as f:
                            expected_output = f.read()

                    # 比對輸出
                    if success and has_expected and user_output.strip() == expected_output.strip():
                        comparison_result = "通過 ✅"
                        success_count += 1
                    elif not has_expected:
                        comparison_result = "無預期輸出 ⚠️"
                    else:
                        comparison_result = "未通過 ❌"

                    results[input_file] = {
                        "user_output": user_output,
                        "expected_output": expected_output,
                        "comparison_result": comparison_result,
                        "execution_time": exec_time,
                        "has_expected": has_expected
                    }

                except Exception as e:
                    logger.error(f"處理測試案例 {input_file} 失敗: {e}")
                    results[input_file] = {
                        "user_output": f"處理錯誤: {str(e)}",
                        "expected_output": "",
                        "comparison_result": "錯誤 ❌",
                        "execution_time": "0s",
                        "has_expected": False
                    }

        total_count = len(inputs)
        summary = {
            "success_count": success_count,
            "total_count": total_count,
            "success_rate": f"{(success_count/total_count*100):.1f}%" if total_count > 0 else "0%",
            "language": lang,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"評判完成: {lang}, {success_count}/{total_count} 通過")
        return jsonify({"results": results, "summary": summary}), 200

    except Exception as e:
        logger.error(f"評判程式碼失敗: {e}")
        return jsonify({"error": "評判失敗，請稍後再試"}), 500

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """獲取系統設定"""
    try:
        config = load_config()
        settings = config.get("settings", DEFAULT_SETTINGS.copy())
        return jsonify({"settings": settings}), 200
    except Exception as e:
        logger.error(f"獲取設定失敗: {e}")
        return jsonify({"error": "獲取設定失敗"}), 500

@app.route("/api/settings", methods=["POST"])
def update_settings():
    """更新系統設定"""
    try:
        data = request.get_json()
        if not data or "settings" not in data:
            return jsonify({"error": "請提供有效的設定資料"}), 400

        new_settings = data["settings"]
        
        # 驗證設定值
        validation_errors = []
        
        if "execution_time_limit" in new_settings:
            if not isinstance(new_settings["execution_time_limit"], (int, float)) or new_settings["execution_time_limit"] <= 0 or new_settings["execution_time_limit"] > 60:
                validation_errors.append("執行時間限制必須是1-60秒之間的數字")
        
        if "memory_limit" in new_settings:
            if not isinstance(new_settings["memory_limit"], int) or new_settings["memory_limit"] <= 0 or new_settings["memory_limit"] > 1024:
                validation_errors.append("記憶體限制必須是1-1024MB之間的整數")
        
        if "compile_time_limit" in new_settings:
            if not isinstance(new_settings["compile_time_limit"], (int, float)) or new_settings["compile_time_limit"] <= 0 or new_settings["compile_time_limit"] > 60:
                validation_errors.append("編譯時間限制必須是1-60秒之間的數字")
        
        if validation_errors:
            return jsonify({"error": "設定驗證失敗", "details": validation_errors}), 400
        
        # 更新設定
        config = load_config()
        if "settings" not in config:
            config["settings"] = DEFAULT_SETTINGS.copy()
        
        config["settings"].update(new_settings)
        save_config(config)
        
        logger.info(f"設定已更新: {new_settings}")
        return jsonify({"message": "設定更新成功", "settings": config["settings"]}), 200
        
    except Exception as e:
        logger.error(f"更新設定失敗: {e}")
        return jsonify({"error": "更新設定失敗"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 