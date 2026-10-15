# 以下の基本設計とMySQLデータベース設計からPythonプログラムを生成。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
University Management System – Python 実装例
MySQL スキーマ（上記設計）に合わせて SQLAlchemy ORM でモデル化し、
基本ビジネスロジック（学生登録・学科・教員・科目・履修登録・成績入力）を提供します。
"""

from __future__ import annotations

import enum
from datetime import date
from typing import List, Optional

from sqlalchemy import (
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    select,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

# ----------------------------------------------------------------------
# Enum 定義（DB の ENUM カラムと同期）
# ----------------------------------------------------------------------
class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"
    Other = "Other"


class StatusStudentEnum(str, enum.Enum):
    active = "active"
    graduated = "graduated"
    withdrawn = "withdrawn"


class StatusEnrollmentEnum(str, enum.Enum):
    registered = "registered"
    withdrawn = "withdrawn"
    failed = "failed"


class SemesterEnum(str, enum.Enum):
    Spring = "Spring"
    Summer = "Summer"
    Fall = "Fall"
    Winter = "Winter"


class LetterGradeEnum(str, enum.Enum):
    A = "A"
    A_ = "A-"
    B = "B"
    B_ = "B-"
    C = "C"
    C_ = "C-"
    D = "D"
    F = "F"


# ----------------------------------------------------------------------
# ORM モデル
# ----------------------------------------------------------------------
Base = declarative_base()


class Student(Base):
    __tablename__ = "students"

    student_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=True)
    gender = Column(Enum(GenderEnum), default=GenderEnum.Other)
    email = Column(String(200), unique=True, nullable=True)
    phone = Column(String(30), nullable=True)
    address = Column(Text, nullable=True)
    enrollment_year = Column(Integer, nullable=False)
    status = Column(Enum(StatusStudentEnum), default=StatusStudentEnum.active)

    # リレーション
    enrollments = relationship(
        "Enrollment", back_populates="student", cascade="all, delete-orphan"
    )


class Department(Base):
    __tablename__ = "departments"

    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(100), unique=True, nullable=False)
    dean_id = Column(Integer, ForeignKey("students.student_id"), nullable=True)

    courses = relationship("Course", back_populates="department")
    instructors = relationship("Instructor", back_populates="department")


class Instructor(Base):
    __tablename__ = "instructors"

    instructor_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    title = Column(String(50), nullable=True)
    email = Column(String(200), unique=True, nullable=True)
    phone = Column(String(30), nullable=True)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), nullable=False)

    department = relationship("Department", back_populates="instructors")
    courses = relationship("Course", back_populates="instructor")


class Course(Base):
    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), nullable=False)
    code = Column(String(20), unique=True, nullable=False)  # e.g. CS101
    name = Column(String(200), nullable=False)
    credit = Column(SmallInteger, nullable=False)
    semester = Column(Enum(SemesterEnum), nullable=False)
    year = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    department = relationship("Department", back_populates="courses")
    instructor = relationship("Instructor", uselist=False, back_populates="courses")
    enrollments = relationship("Enrollment", back_populates="course")


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.course_id"), nullable=False)
    term = Column(String(10), nullable=False)          # e.g. "2024S"
    registration_date = Column(Date, default=func.current_date)
    status = Column(Enum(StatusEnrollmentEnum), default=StatusEnrollmentEnum.registered)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    grades = relationship("Grade", back_populates="enrollment", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "term", name="uq_student_course_term"),
    )


class Grade(Base):
    __tablename__ = "grades"

    grade_id = Column(Integer, primary_key=True, autoincrement=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.enrollment_id"), nullable=False)
    score = Column(SmallInteger, nullable=False)                     # 0‑100
    letter_grade = Column(Enum(LetterGradeEnum), nullable=False)
    evaluation_date = Column(Date, default=func.current_date)
    remarks = Column(Text, nullable=True)

    enrollment = relationship("Enrollment", back_populates="grades")


# ----------------------------------------------------------------------
# DB 接続設定
# ----------------------------------------------------------------------
def get_engine(db_url: str = "mysql+pymysql://user:password@localhost/university"):
    """
    必要に応じて環境変数や .env から取得した URL を渡すこと。
    デフォルトはローカル MySQL 用サンプルです。
    """
    return create_engine(db_url, echo=False, future=True)


SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


# ----------------------------------------------------------------------
# ビジネスロジック
# ----------------------------------------------------------------------
def add_student(
    session: Session,
    *,
    name: str,
    birth_date: Optional[date],
    gender: GenderEnum = GenderEnum.Other,
    email: Optional[str],
    phone: Optional[str],
    address: Optional[str],
    enrollment_year: int,
    status: StatusStudentEnum = StatusStudentEnum.active,
) -> Student:
    stu = Student(
        name=name,
        birth_date=birth_date,
        gender=gender,
        email=email,
        phone=phone,
        address=address,
        enrollment_year=enrollment_year,
        status=status,
    )
    session.add(stu)
    session.flush()  # ID を取得したい場合に利用
    return stu


def add_department(
    session: Session,
    *,
    dept_name: str,
    dean_id: Optional[int] = None,
) -> Department:
    dept = Department(dept_name=dept_name, dean_id=dean_id)
    session.add(dept)
    session.flush()
    return dept


def add_instructor(
    session: Session,
    *,
    name: str,
    title: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    dept_id: int,
) -> Instructor:
    instr = Instructor(
        name=name,
        title=title,
        email=email,
        phone=phone,
        dept_id=dept_id,
    )
    session.add(instr)
    session.flush()
    return instr


def add_course(
    session: Session,
    *,
    dept_id: int,
    code: str,
    name: str,
    credit: int,
    semester: SemesterEnum,
    year: int,
    description: Optional[str] = None,
) -> Course:
    # 担当教員は dept 内の任意の Instructor を後から紐付けても OK
    course = Course(
        dept_id=dept_id,
        code=code,
        name=name,
        credit=credit,
        semester=semester,
        year=year,
        description=description,
    )
    session.add(course)
    session.flush()
    return course


def assign_instructor_to_course(
    session: Session,
    *,
    course_id: int,
    instructor_id: int,
) -> None:
    course = session.get(Course, course_id)
    if not course:
        raise ValueError(f"Course {course_id} not found")
    instructor = session.get(Instructor, instructor_id)
    if not instructor:
        raise ValueError(f"Instructor {instructor_id} not found")
    # 同一学科かどうかのチェック（ビジネスルール）
    if course.department.dept_id != instructor.department.dept_id:
        raise ValueError("Instructor と Course が所属学科一致しません")
    course.instructor = instructor


def enroll_student(
    session: Session,
    *,
    student_id: int,
    course_id: int,
    term: str,
    registration_date: Optional[date] = None,
    status: StatusEnrollmentEnum = StatusEnrollmentEnum.registered,
) -> Enrollment:
    # 学期・年度が courses に一致するか検証
    course = session.get(Course, course_id)
    if not course:
        raise ValueError(f"Course {course_id} not found")

    # term の形式は "YYYY{S|M|F|W}" と仮定
    try:
        year_str, season_char = term[:-1], term[-1]
        term_year = int(year_str)
        season_map = {"S": SemesterEnum.Spring,
                      "M": SemesterEnum.Summer,
                      "F": SemesterEnum.Fall,
                      "W": SemesterEnum.Winter}
        expected_semester = season_map[season_char.upper()]
    except Exception as exc:
        raise ValueError("Invalid term format") from exc

    if course.year != term_year or course.semester != expected_semester:
        raise ValueError(
            f"Term {term} does not match Course {course.code} ({course.semester} {course.year})"
        )

    # 重複登録防止は UNIQUE 制約で保証されるが、明示的にチェックも可
    existing = (
        session.query(Enrollment)
        .filter_by(student_id=student_id, course_id=course_id, term=term)
        .first()
    )
    if existing:
        raise ValueError("Enrollment already exists for this student/course/term")

    enr = Enrollment(
        student_id=student_id,
        course_id=course_id,
        term=term,
        registration_date=registration_date or date.today(),
        status=status,
    )
    session.add(enr)
    session.flush()
    return enr


def input_grade(
    session: Session,
    *,
    enrollment_id: int,
    score: int,
    letter_grade: LetterGradeEnum,
    evaluation_date: Optional[date] = None,
    remarks: Optional[str] = None,
) -> Grade:
    if not (0 <= score <= 100):
        raise ValueError("Score must be between 0 and 100")

    enr = session.get(Enrollment, enrollment_id)
    if not enr:
        raise ValueError(f"Enrollment {enrollment_id} not found")

    grade = Grade(
        enrollment_id=enrollment_id,
        score=score,
        letter_grade=letter_grade,
        evaluation_date=evaluation_date or date.today(),
        remarks=remarks,
    )
    session.add(grade)
    session.flush()
    return grade


# ----------------------------------------------------------------------
# サンプル実行（ユニットテスト感覚で呼び出せます）
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # データベース作成（初回のみ実行してください）
    # engine = get_engine()
    # Base.metadata.create_all(engine)

    with SessionLocal() as sess:
        # ① 学生登録
        alice = add_student(
            sess,
            name="Alice Tanaka",
            birth_date=date(2000, 4, 15),
            gender=GenderEnum.F,
            email="alice@example.com",
            phone="090-1234-5678",
            address="Tokyo",
            enrollment_year=2022,
        )
        print(f"Added student id={alice.student_id}")

        # ② 学科・教員登録
        cs_dept = add_department(sess, dept_name="Computer Science")
        dr_smith = add_instructor(
            sess,
            name="Dr. John Smith",
            title="Professor",
            email="john.smith@univ.ac.jp",
            phone="03-1111-2222",
            dept_id=cs_dept.dept_id,
        )
        print(f"Dept id={cs_dept.dept_id}, Instructor id={dr_smith.instructor_id}")

        # ③ 科目追加
        cs101 = add_course(
            sess,
            dept_id=cs_dept.dept_id,
            code="CS101",
            name="Introduction to Programming",
            credit=3,
            semester=SemesterEnum.Fall,
            year=2024,
            description="Basic programming concepts.",
        )
        print(f"Course id={cs101.course_id}")

        # ④ 担当教員割り当て
        assign_instructor_to_course(sess, course_id=cs101.course_id, instructor_id=dr_smith.instructor_id)

        # ⑤ 履修登録
        term = "2024F"
        enr = enroll_student(sess, student_id=alice.student_id, course_id=cs101.course_id, term=term)
        print(f"Enrollment id={enr.enrollment_id}")

        # ⑥ 成績入力
        grade = input_grade(
            sess,
            enrollment_id=enr.enrollment_id,
            score=92,
            letter_grade=LetterGradeEnum.A,
            remarks="Excellent performance.",
        )
        print(f"Grade id={grade.grade_id}, score={grade.score}")

        # コミットして永続化
        sess.commit()
```

**ポイント**

* `sqlalchemy`（>=2.0）を使用し、テーブル構造は質問中の CREATE TABLE と完全一致させました。  
* 列型・制約は `Column` オプションで表現し、`ENUM` は Python の `enum.Enum` と同期させています。  
* 各ビジネスステップ（学生・学科・教員・科目・履修・成績）は関数として切り出し、例外でエラーハンドリングしています。  
* 最下部の `if __name__ == "__main__"` 部分は動作確認用のサンプルシナリオです。実運用時は適宜削除またはテストコードへ移行してください。
