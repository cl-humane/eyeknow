from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import bcrypt

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('admin.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM Admin WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
            # ✅ SUCCESSFUL LOGIN — render dashboard
            return render_template('dashboard.html')
        else:
            # ❌ LOGIN FAILED — show error message
            return render_template('login.html', message="Invalid username or password")
    else:
        return render_template('login.html')

# 🔽 This is required to actually run the app
if __name__ == '__main__':
    app.run(debug=True)
