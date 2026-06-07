import streamlit as st
import sqlite3
import datetime
import hashlib

# --- データベースの初期設定 ---
def init_db():
    conn = sqlite3.connect("minishare.db")
    c = conn.cursor()
    # 1. ユーザーテーブル（アイコン画像はバイナリデータとして保存）
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            icon_bytes BLOB
        )
    """)
    # 2. 投稿テーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text TEXT,
            time TEXT
        )
    """)
    # 3. DMテーブル
    c.execute("""
        CREATE TABLE IF NOT EXISTS dms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            text TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

# パスワードを暗号化（ハッシュ化）する関数
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hash(password) == hashed_text

init_db()

# --- アプリの設定 ---
st.set_page_config(page_title="MiniShare", page_icon="🕊️", layout="centered")

# セッション状態の初期化
if "user" not in st.session_state:
    st.session_state.user = None

# --- ログイン・サインアップ画面 ---
if st.session_state.user is None:
    st.title("🕊️ MiniShare へようこそ")
    menu = ["ログイン", "新アカウント作成"]
    choice = st.sidebar.selectbox("メニュー", menu)

    if choice == "新アカウント作成":
        st.subheader("👤 新しいアカウントを作る")
        new_user = st.text_input("ユーザー名（英語・数字推奨）", max_chars=15)
        new_password = st.text_input("パスワード", type="password")
        uploaded_file = st.file_uploader("アイコン画像を選択（任意）", type=["png", "jpg", "jpeg"])
        
        if st.button("登録する", type="primary"):
            if not new_user or not new_password:
                st.error("ユーザー名とパスワードを入力してください。")
            else:
                conn = sqlite3.connect("minishare.db")
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username=?", (new_user,))
                if c.fetchone():
                    st.error("そのユーザー名はすでに使われています。")
                else:
                    icon_data = uploaded_file.read() if uploaded_file else None
                    c.execute("INSERT INTO users VALUES (?,?,?)", (new_user, make_hash(new_password), icon_data))
                    conn.commit()
                    st.success("アカウントが作成されました！ログインしてください。")
                conn.close()

    elif choice == "ログイン":
        st.subheader("🔒 ログイン")
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        
        if st.button("ログイン", type="primary"):
            conn = sqlite3.connect("minishare.db")
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (username,))
            result = c.fetchone()
            conn.close()
            
            if result and check_hashes(password, result[0]):
                st.session_state.user = username
                st.success(f"{username} としてログインしました")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが違います。")

# --- ログイン後のメイン画面 ---
else:
    # ユーザーのアイコンを取得する関数
    def get_user_icon(username):
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT icon_bytes FROM users WHERE username=?", (username,))
        res = c.fetchone()
        conn.close()
        if res and res[0]:
            return res[0] # 保存された画像データ
        return "👤" # 画像がない場合はデフォルトの絵文字

    # サイドバーにログアウトボタン
    st.sidebar.write(f"ログイン中: **{st.session_state.user}**")
    if st.sidebar.button("ログアウト"):
        st.session_state.user = None
        st.rerun()

    # タブの作成
    tab1, tab2, tab3 = st.tabs(["🏠 タイムライン", "💌 DM (ダイレクトメッセージ)", "⚙️ プロフィール設定"])

    # ----------------------------------------------------
    # タブ1: タイムライン
    # ----------------------------------------------------
    with tab1:
        st.subheader("タイムライン")
        
        # 投稿フォーム
        user_text = st.text_area("いまどうしてる？", max_chars=140, key="tl_input", placeholder="ここにつぶやきを入力")
        if st.button("つぶやく", type="primary"):
            if user_text.strip():
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                conn = sqlite3.connect("minishare.db")
                c = conn.cursor()
                c.execute("INSERT INTO posts (username, text, time) VALUES (?,?,?)", (st.session_state.user, user_text, now))
                conn.commit()
                conn.close()
                st.rerun()

        st.markdown("---")
        
        # 投稿の表示
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT username, text, time FROM posts ORDER BY id DESC")
        posts = c.fetchall()
        conn.close()

        for username, text, time in posts:
            icon = get_user_icon(username)
            with st.chat_message("user", avatar=icon):
                st.write(f"**{username}**  <small style='color:gray;'>{time}</small>", unsafe_allow_html=True)
                st.write(text)

    # ----------------------------------------------------
    # タブ2: DM (ダイレクトメッセージ)
    # ----------------------------------------------------
    with tab2:
        st.subheader("💌 ダイレクトメッセージ")
        
        # メッセージを送る相手を選ぶ（自分以外のユーザーリストを取得）
        conn = sqlite3.connect("minishare.db")
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE username != ?", (st.session_state.user,))
        users = [row[0] for row in c.fetchall()]
        conn.close()
        
        if not users:
            st.info("まだ他のユーザーが登録されていません。")
        else:
            receiver = st.selectbox("話す相手を選ぶ", users)
            
            # DMの送信フォーム
            dm_text = st.text_input(f"{receiver} へメッセージを送る")
            if st.button("DMを送信"):
                if dm_text.strip():
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    conn = sqlite3.connect("minishare.db")
                    c = conn.cursor()
                    c.execute("INSERT INTO dms (sender, receiver, text, time) VALUES (?,?,?,?)", (st.session_state.user, receiver, dm_text, now))
                    conn.commit()
                    conn.close()
                    st.rerun()
            
            st.markdown("### チャット履歴")
            # 自分と相手の間のDM履歴のみを取得
            conn = sqlite3.connect("minishare.db")
            c = conn.cursor()
            c.execute("""
                SELECT sender, text, time FROM dms 
                WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
                ORDER BY id DESC
            """, (st.session_state.user, receiver, receiver, st.session_state.user))
            dms = c.fetchall()
            conn.close()
            
            for sender, text, time in dms:
                icon = get_user_icon(sender)
                # 自分が送ったものは右寄せっぽく見せる（Streamlitの仕様上、名前で区別）
                is_me = " (あなた)" if sender == st.session_state.user else ""
                with st.chat_message("user", avatar=icon):
                    st.write(f"**{sender}{is_me}**  <small style='color:gray;'>{time}</small>", unsafe_allow_html=True)
                    st.write(text)

    # ----------------------------------------------------
    # タブ3: プロフィール設定
    # ----------------------------------------------------
    with tab3:
        st.subheader("⚙️ プロフィール設定")
        st.write("アイコン画像を更新できます。")
        new_icon_file = st.file_uploader("新しいアイコン画像を選択", type=["png", "jpg", "jpeg"], key="profile_icon")
        
        if st.button("アイコンを更新"):
            if new_icon_file:
                icon_data = new_icon_file.read()
                conn = sqlite3.connect("minishare.db")
                c = conn.cursor()
                c.execute("UPDATE users SET icon_bytes=? WHERE username=?", (icon_data, st.session_state.user))
                conn.commit()
                conn.close()
                st.success("アイコンを更新しました！")
                st.rerun()
            else:
                st.error("画像を選択してください。")
