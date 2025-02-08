import os
import subprocess
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import zipfile
import io

app = Flask(__name__)
CORS(app)

# 測試資料夾
TESTCASE_DIR = "/app/testcases"

# 確保目錄存在
os.makedirs(TESTCASE_DIR, exist_ok=True)

@app.route("/")
def home():
    return send_file('index.html')

# 提供靜態資源
@app.route('/favicons_io/<path:filename>')
def static_files(filename):
    return send_from_directory('favicons_io', filename)

# 上傳測試資料 (支援 .in 和 .out 檔案)
@app.route("/upload", methods=["POST"])
def upload_testcase():
    name = request.form.get("name")
    test_input = request.form.get("input")
    test_output = request.form.get("output")

    if not name or not test_input:
        return jsonify({"error": "請提供測試檔名和輸入內容"}), 400

    input_filename = f"{name}.in"
    output_filename = f"{name}.out"

    with open(os.path.join(TESTCASE_DIR, input_filename), "w") as f:
        f.write(test_input)

    if test_output:
        with open(os.path.join(TESTCASE_DIR, output_filename), "w") as f:
            f.write(test_output)

    return jsonify({"message": f"{name} 測試資料上傳成功"}), 200

# 列出測試資料
@app.route("/testcases", methods=["GET"])
def list_testcases():
    files = os.listdir(TESTCASE_DIR)
    return jsonify(files), 200

@app.route("/testcases/<name>", methods=["GET"])
def get_testcase(name):
    input_filename = os.path.join(TESTCASE_DIR, f"{name}.in")
    output_filename = os.path.join(TESTCASE_DIR, f"{name}.out")

    if not os.path.exists(input_filename):
        return jsonify({"error": "測試資料不存在"}), 404

    with open(input_filename, "r") as f:
        test_input = f.read()

    test_output = ""
    if os.path.exists(output_filename):
        with open(output_filename, "r") as f:
            test_output = f.read()

    return jsonify({"input": test_input, "output": test_output}), 200

# 匯出測試資料
@app.route("/export", methods=["GET"])
def export_testcases():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zipf:
        for root, _, files in os.walk(TESTCASE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, TESTCASE_DIR))
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name="testcases.zip")

# 匯入測試資料
@app.route("/import", methods=["POST"])
def import_testcases():
    if 'files' not in request.files:
        return jsonify({"error": "請提供要匯入的檔案"}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "檔案無效"}), 400

    for file in files:
        filename = os.path.basename(file.filename)
        if filename.endswith('.in') or filename.endswith('.out'):
            file_path = os.path.join(TESTCASE_DIR, filename)
            file.save(file_path)

    return jsonify({"message": "測試資料匯入成功"}), 200

# 刪除測試資料
@app.route("/delete", methods=["POST"])
def delete_testcases():
    testcases = request.json.get("testcases", [])
    if not testcases:
        return jsonify({"error": "請提供要刪除的測試資料"}), 400

    for testcase in testcases:
        input_file = os.path.join(TESTCASE_DIR, testcase + ".in")
        output_file = os.path.join(TESTCASE_DIR, testcase + ".out")
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

    return jsonify({"message": "測試資料刪除成功"}), 200

import tempfile

@app.route("/judge", methods=["POST"])
def judge_code():
    code = request.form.get("code")
    lang = request.form.get("lang")

    if not code or lang not in ["cpp", "java", "python"]:
        return jsonify({"error": "請提供程式碼和語言 (cpp, java, python)"}), 400

    # 建立臨時目錄
    with tempfile.TemporaryDirectory() as temp_dir:
        # 儲存程式碼
        if lang == "cpp":
            code_file = os.path.join(temp_dir, "main.cpp")
            exec_cmd = ["g++", "main.cpp", "-o", "main"]
            run_cmd = ["./main"]
        elif lang == "java":
            code_file = os.path.join(temp_dir, "Main.java")
            exec_cmd = ["javac", "Main.java"]
            run_cmd = ["java", "Main"]
        else:
            code_file = os.path.join(temp_dir, "main.py")
            exec_cmd = ["python3", "main.py"]
            run_cmd = ["python3", "main.py"]

        with open(code_file, "w") as f:
            f.write(code)

        # 編譯程式碼 (如果需要)
        if lang in ["cpp", "java"]:
            try:
                subprocess.run(exec_cmd, check=True, capture_output=True, text=True, cwd=temp_dir)
            except subprocess.CalledProcessError as e:
                return jsonify({"error": f"編譯錯誤: {e.stderr}"}), 400

        # 取得測試資料
        inputs = sorted([f for f in os.listdir(TESTCASE_DIR) if f.endswith(".in")])
        results = {}
        success_count = 0

        for input_file in inputs:
            output_file = input_file.replace(".in", ".out")
            input_path = os.path.join(TESTCASE_DIR, input_file)
            output_path = os.path.join(TESTCASE_DIR, output_file)

            # 執行程式
            try:
                result = subprocess.run(run_cmd, input=open(input_path).read(),
                                        text=True, capture_output=True, timeout=3, cwd=temp_dir)
                user_output = result.stdout
                if result.returncode != 0:
                    user_output += f"\n錯誤: {result.stderr}"
            except subprocess.TimeoutExpired:
                results[input_file] = {
                    "user_output": "執行時間過長",
                    "expected_output": "",
                    "comparison_result": "未通過 ❌"
                }
                continue
            except subprocess.CalledProcessError as e:
                user_output = f"執行錯誤: {e.stderr}"
                results[input_file] = {
                    "user_output": user_output,
                    "expected_output": "",
                    "comparison_result": "未通過 ❌"
                }
                continue

            # 讀取預期輸出
            expected_output = open(output_path).read() if os.path.exists(output_path) else "無預期輸出"

            # 比對輸出
            if user_output.strip() == expected_output.strip():
                comparison_result = "通過 ✅"
                user_output = user_output.strip()
                expected_output = expected_output.strip()
                success_count += 1
            else:
                comparison_result = "未通過 ❌"

            results[input_file] = {
                "user_output": user_output,
                "expected_output": expected_output,
                "comparison_result": comparison_result
            }

        total_count = len(inputs)
        summary = {
            "success_count": success_count,
            "total_count": total_count
        }

        return jsonify({"results": results, "summary": summary}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)