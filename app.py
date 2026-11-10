import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import qrcode
from PIL import Image
import io


# ================= 1. 数据库配置 =================
def init_db():
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            room TEXT NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            phone TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()

# ================= 2. 基础数据定义 =================
TIME_SLOTS = {
    "第1节": "08:30-09:15", "第2节": "09:25-10:10",
    "第3节": "10:35-11:20", "第4节": "11:30-12:15",
    "第5节": "14:00-14:45", "第6节": "14:55-15:40",
    "第7节": "16:00-16:45", "第8节": "16:55-17:40",
    "第9节": "19:20-20:05", "第10节": "20:15-21:00"
}

ROOMS = {
    "513": "空旷教室",
    "514": "团辅室（有座位、投影）",
    "515": "沙盘室（五彩斑斓）",
    "516": "团辅室（有座位、投影）"
}


# ================= 3. 业务逻辑判断 =================
def is_valid_date(target_date):
    return target_date > date.today()


def is_valid_time_slot(target_date, time_slot):
    weekday = target_date.weekday()
    if weekday in [0, 1, 2, 3]:
        return True
    elif weekday == 4:
        if time_slot in ["第1节", "第2节", "第3节", "第4节", "第5节", "第6节", "第7节", "第8节"]: return True
        return False
    elif weekday == 5:
        return False
    elif weekday == 6:
        if time_slot in ["第9节", "第10节"]: return True
        return False
    return False


def check_room_available(room, target_date, time_slot):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM reservations WHERE room=? AND date=? AND time_slot=?",
              (room, target_date.strftime("%Y-%m-%d"), time_slot))
    result = c.fetchone()
    conn.close()
    return result is None


def check_user_conflict(name, target_date, time_slot):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM reservations WHERE name=? AND date=? AND time_slot=?",
              (name, target_date.strftime("%Y-%m-%d"), time_slot))
    result = c.fetchone()
    conn.close()
    return result is None


def add_reservation(name, class_name, room, target_date, time_slot, phone):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO reservations (name, class_name, room, date, time_slot, phone, create_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, class_name, room, target_date.strftime("%Y-%m-%d"), time_slot, phone,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_schedule(target_date):
    conn = sqlite3.connect('booking.db')
    query = "SELECT room, time_slot FROM reservations WHERE date=?"
    df = pd.read_sql_query(query, conn, params=(target_date.strftime("%Y-%m-%d"),))
    conn.close()
    schedule = []
    for slot in TIME_SLOTS.keys():
        row = {"时间段": f"{slot} ({TIME_SLOTS[slot]})"}
        for room in ROOMS.keys():
            booked = not df[(df['room'] == room) & (df['time_slot'] == slot)].empty
            row[room] = "❌ 已预约" if booked else "✅ 可预约"
        schedule.append(row)
    return pd.DataFrame(schedule)


# ================= 4. 界面设计 =================
st.set_page_config(page_title="校心理中心教室预约平台", page_icon="🏫", layout="wide")

st.sidebar.title("导航菜单")

# ====== 二维码生成功能 ======
st.sidebar.markdown("---")
st.sidebar.subheader("📱 扫码进入平台")
share_url = st.sidebar.text_input("网址", value="http://localhost:8501")
if share_url:
    try:
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.sidebar.image(buf.getvalue(), caption="微信扫一扫", use_column_width=True)
    except Exception:
        pass
st.sidebar.markdown("---")
# ==================================

role = st.sidebar.radio("请选择您的身份：", ["学生/老师", "管理员"])

# --- 学生/老师端 ---
if role == "学生/老师":
    st.title("🏫 校心理中心教室预约平台")
    st.info("📍 地点：科技馆5楼 | 📞 中心电话：0971-5311690")

    with st.expander("📖 请详细阅读预约教室细则（必读）", expanded=False):
        st.markdown("""
        1. 爱护公共器材与多媒体设备，轻拿轻放，勿违规操作。
        2. 保持场地整洁，垃圾入桶，不吸烟、不吐痰，活动结束自行清理杂物。
        3. 个人物品妥善保管，贵重物品随身携带，场地内遗失责任自负。
        4. 场地优先使用权归青海大学心理健康教育中心所属。
        5. 遵守法规，不大声喧哗，按规定人数、时间、类型活动，不得损坏消防等安全设施。
        6. **每天同一时间段只可预约一个教室。**
        7. **放映PPT需要自行带电脑进行投屏。**
        8. **可预约时间为工作日时间，周五晚上～周天下午不可预约，周天晚上可预约。**
        9. **至少提前一天进行预约。**

        **教室介绍：**
        * 513：空旷教室
        * 514，516：有座位有投影的团辅室
        * 515：五彩斑斓的沙盘室
        """)

    st.subheader("📅 查看教室预约状态")
    view_date = st.date_input("选择要查看的日期", min_value=date.today() + timedelta(days=1))

    if view_date:
        schedule_df = get_schedule(view_date)
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)

    st.subheader("📝 提交预约申请")
    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("借用负责人姓名")
            class_name = st.text_input("学院年级班级 (例：计算机学院22级1班)")
            phone = st.text_input("联系电话")
        with col2:
            target_date = st.date_input("预约日期", min_value=date.today() + timedelta(days=1))
            time_slot = st.selectbox("预约时间段", list(TIME_SLOTS.keys()),
                                     format_func=lambda x: f"{x} ({TIME_SLOTS[x]})")
            room = st.selectbox("预约教室", list(ROOMS.keys()), format_func=lambda x: f"{x} - {ROOMS[x]}")

        submit = st.form_submit_button("确认预约")

        if submit:
            if not all([name, class_name, phone, target_date, time_slot, room]):
                st.error("请填写所有必填信息！")
            elif not is_valid_date(target_date):
                st.error("预约失败：必须至少提前一天预约！")
            elif not is_valid_time_slot(target_date, time_slot):
                st.error("预约失败：周五晚上至周日下午不可预约，仅周天晚上可预约！")
            elif not check_room_available(room, target_date, time_slot):
                st.error(f"预约失败：{room}教室在 {target_date} 的 {time_slot} 已被预约，请选择其他时间或教室。")
            elif not check_user_conflict(name, target_date, time_slot):
                st.error("预约失败：您（该姓名）在同一天同一时间段已预约了一个教室，不可重复预约！")
            else:
                add_reservation(name, class_name, room, target_date, time_slot, phone)
                st.success(f"🎉 预约成功！请按时到达科技馆5楼 {room}教室。")
                st.balloons()

# --- 管理员端 ---
else:
    st.title("🔐 管理员控制台")
    password = st.sidebar.text_input("请输入管理员密码", type="password")

    if password == st.secrets.get("ADMIN_PASSWORD", "admin123"):
        st.success("管理员身份已验证")

        conn = sqlite3.connect('booking.db')
        df = pd.read_sql_query("SELECT * FROM reservations ORDER BY date DESC, time_slot", conn)
        conn.close()

        if df.empty:
            st.info("目前没有任何预约记录。")
        else:
            st.subheader("所有预约记录（包含隐私信息）")
            st.dataframe(df, use_container_width=True)

            st.subheader("删除预约")
            delete_id = st.number_input("请输入要删除的预约记录 ID", min_value=1, step=1)
            if st.button("确认删除"):
                conn_del = sqlite3.connect('booking.db')
                c = conn_del.cursor()
                c.execute("DELETE FROM reservations WHERE id=?", (delete_id,))
                conn_del.commit()
                conn_del.close()
                st.success(f"ID为 {delete_id} 的预约已删除。")
                st.rerun()
    elif password != "":
        st.error("密码错误，请重新输入。")