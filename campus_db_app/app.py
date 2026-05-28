import streamlit as st
import mysql.connector
import pandas as pd

st.set_page_config(page_title="학사 관리 시스템", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f0f4f8; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        border: none;
        width: 100%;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        font-weight: bold;
    }
    h1 { color: #2c3e50; text-align: center; }
    h2 { color: #34495e; }
    .stSelectbox label { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def get_conn():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root1234",
        database="campus_db"
    )

conn = get_conn()
cursor = conn.cursor()

st.markdown("# 🏫 학사 관리 통합 시스템")
st.markdown("---")

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/graduation-cap.png", width=80)
    st.markdown("## 📌 메뉴")
    st.markdown("학과, 학생, 교수,\n수강 정보를 관리합니다.")
    st.markdown("---")
    if st.button("🔄 새로고침"):
        st.rerun()
    st.markdown("---")
    st.caption("학사 관리 시스템 v3.0")

tab1, tab2, tab3 = st.tabs(["✏️ 정보 등록", "📋 수강 신청", "📊 현황 조회"])

cursor.execute("SELECT department_code, department_name FROM department")
depts = cursor.fetchall()
dept_options = {f"{d[0]}: {d[1]}": d[0] for d in depts}

with tab1:
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### 👨‍🎓 학생 등록")
        with st.form("student_form"):
            s_name = st.text_input("학생 이름")
            s_height = st.number_input("키 (cm)", value=170.0, step=0.1)
            s_dept = st.selectbox("소속 학과", list(dept_options.keys()))
            submitted = st.form_submit_button("➕ 학생 추가")
            if submitted:
                cursor.execute(
                    "INSERT INTO student (student_name, student_height, department_code) VALUES (%s, %s, %s)",
                    (s_name, s_height, dept_options[s_dept]))
                conn.commit()
                st.success(f"✅ {s_name} 학생이 등록됐습니다!")

    with col2:
        st.markdown("### 👨‍🏫 교수 등록")
        with st.form("professor_form"):
            p_name = st.text_input("교수 성함")
            p_dept = st.selectbox("소속 학과", list(dept_options.keys()))
            submitted2 = st.form_submit_button("➕ 교수 추가")
            if submitted2:
                cursor.execute(
                    "INSERT INTO professor (professor_name, department_code) VALUES (%s, %s)",
                    (p_name, dept_options[p_dept]))
                conn.commit()
                st.success(f"✅ {p_name} 교수가 등록됐습니다!")

with tab2:
    st.markdown("### 📋 수강 신청")
    cursor.execute("SELECT student_id, student_name FROM student")
    students = cursor.fetchall()
    cursor.execute("SELECT course_code, course_name FROM course")
    courses = cursor.fetchall()

    student_options = {f"{s[0]}: {s[1]}": s[0] for s in students}
    course_options = {f"{c[0]}: {c[1]}": c[0] for c in courses}

    with st.form("course_form"):
        col1, col2 = st.columns(2)
        with col1:
            sel_student = st.selectbox("👨‍🎓 학생 선택", list(student_options.keys()))
        with col2:
            sel_course = st.selectbox("📚 과목 선택", list(course_options.keys()))
        submitted3 = st.form_submit_button("📝 수강 신청")
        if submitted3:
            try:
                cursor.execute(
                    "INSERT INTO student_course (student_id, course_code) VALUES (%s, %s)",
                    (student_options[sel_student], course_options[sel_course]))
                conn.commit()
                st.success("✅ 수강 신청 완료!")
            except:
                st.error("❌ 이미 신청된 수강입니다!")

with tab3:
    st.markdown("### 📊 현황 조회")
    menu = st.selectbox("테이블 선택",
        ["department", "student", "professor", "course", "student_course"])
    cursor.execute(f"SELECT * FROM {menu}")
    rows = cursor.fetchall()
    columns = [i[0] for i in cursor.description]
    df = pd.DataFrame(rows, columns=columns)
    st.dataframe(df, use_container_width=True)