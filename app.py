import os
import subprocess
from flask import Flask, request, jsonify, send_file
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
    return "Judge 伺服器運行中 (僅限 localhost)！"

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

# 匯出測試資料
@app.route("/export", methods=["GET"])
def export_testcases():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in os.listdir(TESTCASE_DIR):
            file_path = os.path.join(TESTCASE_DIR, filename)
            zf.write(file_path, filename)
    memory_file.seek(0)
    return send_file(memory_file, attachment_filename='testcases.zip', as_attachment=True)

# 匯入測試資料
@app.route("/import", methods=["POST"])
def import_testcases():
    if 'file' not in request.files:
        return jsonify({"error": "請提供要匯入的檔案"}), 400

    file = request.files['file']
    if not file:
        return jsonify({"error": "檔案無效"}), 400

    with zipfile.ZipFile(file) as zf:
        zf.extractall(TESTCASE_DIR)

    return jsonify({"message": "測試資料匯入成功"}), 200

# 刪除測試資料
@app.route("/delete", methods=["POST"])
def delete_testcases():
    testcases = request.json.get("testcases", [])
    if not testcases:
        return jsonify({"error": "請提供要刪除的測試資料"}), 400

    for testcase in testcases:
        input_file = os.path.join(TESTCASE_DIR, testcase)
        output_file = os.path.join(TESTCASE_DIR, testcase.replace(".in", ".out"))
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)

    return jsonify({"message": "測試資料刪除成功"}), 200

# 執行測試 (判斷語言後執行)
@app.route("/judge", methods=["POST"])
def judge_code():
    code = request.form.get("code")
    lang = request.form.get("lang")

    if not code or lang not in ["cpp", "java", "python"]:
        return jsonify({"error": "請提供程式碼和語言 (cpp, java, python)"}), 400

    # 儲存程式碼
    if lang == "cpp":
        code_file = "main.cpp"
        exec_cmd = "g++ main.cpp -o main && ./main"
    elif lang == "java":
        code_file = "Main.java"
        exec_cmd = "javac Main.java && java Main"
    else:
        code_file = "main.py"
        exec_cmd = "python3 main.py"

    with open(f"/app/{code_file}", "w") as f:
        f.write(code)

    # 取得測試資料
    inputs = sorted([f for f in os.listdir(TESTCASE_DIR) if f.endswith(".in")])
    results = {}

    for input_file in inputs:
        output_file = input_file.replace(".in", ".out")
        input_path = os.path.join(TESTCASE_DIR, input_file)
        output_path = os.path.join(TESTCASE_DIR, output_file)

        # 執行程式
        try:
            result = subprocess.run(exec_cmd, input=open(input_path).read(),
                                    text=True, capture_output=True, shell=True, timeout=2)
            user_output = result.stdout.strip()
        except subprocess.TimeoutExpired:
            results[input_file] = "執行時間過長"
            continue

        # 讀取預期輸出
        expected_output = open(output_path).read().strip() if os.path.exists(output_path) else "無預期輸出"

        # 比對輸出
        if user_output == expected_output:
            results[input_file] = "通過 ✅"
        else:
            results[input_file] = f"錯誤 ❌ (預期: {expected_output} / 輸出: {user_output})"

    return jsonify(results), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)