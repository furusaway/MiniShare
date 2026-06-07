import streamlit as st
import sqlite3
import datetime

# --- データベースの初期設定 ---
def init_db():
    conn = sqlite3.connect("sns.db")
    c = conn.cursor()
    # 投稿を保存するテーブル（存在しない場合のみ作成）
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            text TEXT,
            icon TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_posts():
    conn = sqlite3.connect("sns.db")
    c = conn.cursor()
    # 新しい投稿が上に来るように、IDの降順で取得
    c.execute("SELECT name, text, icon, time FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    conn.close()
    return posts

def save_post(name, text, icon, time):
    conn = sqlite3.connect("sns.db")
    c = conn.cursor()
    c.execute("INSERT INTO posts (name, text, icon, time) VALUES (?, ?, ?, ?)", (name, text, icon, time))
    conn.commit()
    conn.close()

# データベースの初期化を実行
init_db()


# --- 10人用の簡易パスワード設定 ---
SECRET_PASSWORD = "secret123"  # 👈 10人に教える共通パスワード（自由に変更してください）


# --- アプリの画面設定 ---
st.set_page_config(page_title="10人のヒミツのSNS", page_icon="💬", layout="centered")


# --- ログインチェック ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # ログイン画面
    st.title("🔒 認証が必要です")
    st.write("このSNSは合言葉を知っている10人だけの限定空間です。")
    
    password_input = st.text_input("合言葉（パスワード）を入力してください", type="password")
    if st.button("入場する"):
        if password_input == SECRET_PASSWORD:
            st.session_state.logged_in = True
            st.success("認証に成功しました！")
            st.rerun()
        else:
            st.error("合言葉が違います。")
            
else:
    # --- ログイン後のメインSNS画面 ---
    st.title("🚀 10人のヒミツのSNS")
    
    # ログアウトボタン（右上に配置）
    col_title, col_logout = st.columns([4, 1])
    with col_logout:
        if st.button("ログアウト"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("---")

    # --- 投稿エリア ---
    st.subheader("📝 いまどうしてる？")
    
    # アイコン選択、名前、本文の入力欄
    col1, col2 = st.columns([1, 3])
    with col1:
        user_icon = st.selectbox("アイコン", ["😊", "🐱", "🐶", "🦊", "😎", "🤖", "🎨", "⚽"])
    with col2:
        user_name = st.text_input("あなたの名前", max_chars=10, placeholder="タロウ")
        
    user_text = st.text_area("メッセージ（140文字まで）", max_chars=140, placeholder="ここに書き込んでね")

    if st.button("投稿する", type="primary"):
        if user_name.strip() == "" or user_text.strip() == "":
            st.error("名前とメッセージの両方を入力してください！")
        else:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            # データベースに保存
            save_post(user_name, user_text, user_icon, now)
            st.success("投稿しました！")
            st.rerun()

    st.markdown("---")

    # --- タイムラインエリア ---
    st.subheader("💬 みんなのタイムライン")

    # データベースから最新の投稿を読み込み
    posts = load_posts()

    if not posts:
        st.info("まだ投稿がありません。最初のつぶやきをどうぞ！")
    else:
        for post in posts:
            name, text, icon, time = post
            # StreamlitのチャットUIを使ってSNS風のデザインに
            with st.chat_message("user", avatar=icon):
                st.write(f"**{name}**  <small style='color:gray;'>{time}</small>", unsafe_allow_html=True)
                st.write(text)
