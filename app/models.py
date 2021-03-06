import datetime
import re
from hashlib import md5
from urllib.parse import urlencode
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app import login
from app import app
from flask_login import UserMixin
from time import time
import jwt
from app.forms import NewProjectForm, UserForm
from flask_babel import _, get_locale, force_locale
from flask import url_for
import json

from sqlalchemy.ext.hybrid import hybrid_property
from string import ascii_letters, digits
import random
import pycountry
import urllib


@login.user_loader
def load_user(id_):
    return User.query.get(int(id_))


@contextmanager
def session_handler():
    session = db.session
    try:
        session.flush()
        yield session
        session.commit()
    except Exception as exp:
        app.logger.error(exp)
        print(exp)
        session.rollback()
        raise exp


class User(UserMixin, db.Model):
    __tablename__ = "user"

    user_id = db.Column("user_id", db.Integer, autoincrement=True, primary_key=True)
    email = db.Column('email', db.String(120), nullable=False, unique=True)
    password = db.Column("password", db.Text(500), nullable=True)
    name = db.Column('name', db.String(64), nullable=False)
    surname = db.Column('surname', db.String(64), nullable=False)
    gender = db.Column("gender", db.String(1), default="m")
    phone = db.Column("phone", db.String(15), nullable=True)
    telegram_u_id = db.Column("telegram_u_id", db.Integer, nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.datetime(1900, 1, 1, 0, 0))

    privacy = db.relationship("UserPrivacy", back_populates="user", uselist=False)
    privileges = db.relationship("UserPrivileges", back_populates="user", uselist=False)

    def __init__(self, email, name, surname, gender, phone):
        self.email = email
        self.name = name
        self.surname = surname
        self.gender = gender
        self.phone = phone
        self.telegram_u_id = None
        self.last_seen = datetime.datetime(year=1900, month=1, day=1, hour=0, minute=0, second=0)
        # self.approved = approved

    def validate_password(self, password):
        return check_password_hash(self.password, password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def get_reset_password_token(self, expires_in=600):
        """
        :param expires_in: time in seconds when token will expire
        :return: token in hash
        """
        return jwt.encode(
            {'reset_password': self.user_id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            tmp_dic = jwt.decode(token, app.config['SECRET_KEY'],
                                 algorithms=['HS256'])
            user_id = tmp_dic.get("reset_password")
            expired = time() > tmp_dic.get("exp", 0)
        except Exception as exp:
            return
        return User.query.get(user_id) if not expired else None

    def get_id(self):
        return self.user_id

    def get_name(self):
        return self.surname + " " + self.name

    def is_online(self):
        return self.last_seen + datetime.timedelta(minutes=3) > datetime.datetime.utcnow()


class UserPrivileges(db.Model):
    __tablename__ = "user_privileges"

    def __init__(self, user_id):
        self.user_id = user_id
        self.is_admin = False

    user_id = db.Column("user_id", db.Integer, db.ForeignKey("user.user_id",
                                                             ondelete="CASCADE", onupdate="CASCADE"), primary_key=True,
                        nullable=False)
    user = db.relationship("User", back_populates="privileges")
    is_admin = db.Column("is_admin", db.Boolean, default=False)


class UserPrivacy(db.Model):
    __tablename__ = "user_privacy"

    def __init__(self, user_id):
        self.user_id = user_id
        self.use_gravatar = False
        self.share_number = False
        self.share_email = False

    user_id = db.Column("user_id", db.Integer, db.ForeignKey("user.user_id",
                                                             ondelete="CASCADE", onupdate="CASCADE"), primary_key=True,
                        nullable=False)
    user = db.relationship("User", back_populates="privacy")
    use_gravatar = db.Column("use_gravatar", db.Boolean, default=True)
    share_number = db.Column("share_number", db.Boolean, default=True)
    share_email = db.Column("share_email", db.Boolean, default=True)


class Project(db.Model):
    __tablename__ = "project"

    project_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    background_url = db.Column(db.String(200), default=True)
    github_url = db.Column(db.String(200), nullable=True)
    website_url = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text(20000), nullable=True)
    created_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    starred = db.Column(db.Boolean, default=False)
    private = db.Column(db.Boolean, default=False)

    def __init__(self, category, title, background_url, github_url, website_url, description):
        self.category = category
        self.title = title
        self.background_url = background_url
        self.github_url = github_url
        self.website_url = website_url
        self.description = description

    def get_bg_image(self):
        return self.background_url or url_for('static', filename='project1.jpg')

    def parse_description(self):
        return "<br>".join(self.description.splitlines()) if self.description else "No description"


# No SQL
class Wedding:
    date: datetime.date = None
    time: datetime.time = None
    remote_id: str = None
    remote_password: str = None
    remote_link: str = None
    invite_message: str = None
    invitees: list = []
    output: dict = {}

    def get_time_display(self, timezone: int = 0) -> str:
        return self.time.replace(hour=self.time.hour + timezone).strftime("%H:%M")

    def get_date_display(self):
        return self.date.strftime("%d %B %Y")

    def get_datetime(self):
        import pytz
        tz = pytz.timezone("CET")
        full_datetime = datetime.datetime(year=self.date.year, month=self.date.month, day=self.date.day,
                                          hour=self.time.hour, minute=self.time.minute)

        return tz.localize(full_datetime)

    def get_datetime_end(self):
        return self.get_datetime() + datetime.timedelta(minutes=30)

    def is_today(self):
        return self.date == datetime.datetime.now().date()

    def load(self, fp: str) -> bool:
        try:
            with open(fp, "r") as file:
                data_raw = file.read()
                file.close()
            data = json.loads(data_raw)
        except:
            self.save(fp)
            return True

        self.date = data.get("date", "")
        if self.date:
            try:
                self.date = datetime.datetime.strptime(self.date, "%m/%d/%Y").date()
            except:
                self.date = None
        self.time = data.get("time", "")
        if self.time:
            try:
                self.time = datetime.datetime.strptime(self.time, "%H:%M").time()
            except:
                self.time = None
        self.remote_id = data.get("remote_id", "")
        self.remote_password = data.get("remote_password", "")
        self.remote_link = data.get("remote_link", "")
        self.invite_message = data.get("invite_message", "")
        self.invitees = [WeddingInvitation(people_=x.get("people"), invited_=x.get("invited"))
                         for x in data.get("invitees")]
        return True

    def update(self, fp: str, data) -> bool:
        self.date = data.date.data
        self.time = data.time.data
        self.remote_id = data.remote_id.data
        self.remote_password = data.remote_password.data
        self.remote_link = data.remote_link.data
        self.invite_message = data.invite_message.data
        self.invitees = [WeddingInvitation(invitee=x) for x in data.invitees if x]
        for people in data.invitees_new.data.split("\n"):
            if people:
                self.invitees.append(WeddingInvitation(people_=people))
        self.save(fp=fp)
        return True

    def save(self, fp: str) -> bool:
        self.parse_to_json()
        with open(fp, "w") as file:
            file.write(json.dumps(self.output, indent=4))
            file.close()
        return True

    def parse_to_json(self):
        # breakpoint()
        self.output = {
            "date": self.date.strftime("%m/%d/%Y") if isinstance(self.date, datetime.date) else self.date,
            "time": self.time.strftime("%H:%M") if isinstance(self.time, datetime.time) else self.time,
            "remote_id": self.remote_id,
            "remote_password": self.remote_password,
            "remote_link": self.remote_link,
            "invite_message": self.invite_message,
            "invitees": [invitee.parse_to_json() for invitee in self.invitees]
        }


class WeddingInvitation:
    people: str = None
    invited: bool = False
    output: dict = {}

    def __init__(self, people_: str = None, invited_: bool = False, invitee=None):
        if not people_ and invitee:
            people_ = invitee.people.data
            invited_ = invitee.invited.data
        self.people = people_
        self.invited = invited_

    def parse_to_json(self):
        self.output = {
            "people": self.people,
            "invited": self.invited
        }
        return self.output


def add_project(category, form):
    with session_handler() as db_session:
        if not isinstance(form, NewProjectForm):
            return False, "Backend form error"
        new_project = Project(
            category=category,
            title=form.title.data,
            background_url=form.background_image.data,
            github_url=form.github_url.data,
            website_url=form.website_url.data,
            description=form.description.data
        )
        db_session.add(new_project)
        db_session.commit()
        return True, "New project has been created"


def modify_project(project_id, form):
    with session_handler() as db_session:
        project = db_session.query(Project).filter(Project.project_id == project_id).first()
        if not isinstance(project, Project):
            return False, "No such project"
        if not isinstance(form, NewProjectForm):
            return False, "Backend form error"
        project.title = form.title.data
        project.background_url = form.background_image.data
        project.github_url = form.github_url.data
        project.website_url = form.website_url.data
        project.description = form.description.data
        db_session.commit()
        return True, "Project has been updated"


def update_project_settings(project_id, req):
    with session_handler() as db_session:
        result = {"success": False, "message": "Unknown server error"}
        project = db_session.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            result["message"] = "No project with ID " + str(project_id)
        else:
            if "private" in req:
                project.private = not project.private
            if "starred" in req:
                project.starred = not project.starred
            db_session.commit()
            result["success"] = True
            result["message"] = "Project settings has been updated"
        return result


def remove_project(project_id):
    with session_handler() as db_session:
        project = db_session.query(Project).filter(Project.project_id == project_id).first()
        if not isinstance(project, Project):
            return False, "No such project"
        db_session.delete(project)
        db_session.commit()
        return True, "Project has been removed"


def get_projects(authenticated: bool) -> (list, list, list):
    with session_handler() as db_session:
        projects = db_session.query(Project)
        if not authenticated:
            projects = projects.filter(Project.private == False)
        projects_private = projects.filter(
            Project.category == "private"
        ).order_by(
            -Project.starred,
            -Project.created_time
        ).all()
        projects_work = projects.filter(
            Project.category == "work"
        ).order_by(
            -Project.starred,
            -Project.created_time
        ).all()
        projects_study = projects.filter(
            Project.category == "study"
        ).order_by(
            -Project.starred,
            -Project.created_time
        ).all()
        return projects_private, projects_work, projects_study


def add_user(form):
    with session_handler() as db_session:
        if not isinstance(form, UserForm):
            return False, "Backend error"
        ex_user = db_session.query(User).filter(User.email == form.email.data).first()
        if ex_user:
            return False, f"User with email {form.email.data} already exists"
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            surname=form.surname.data,
            phone=form.phone.data,
            gender=form.gender.data
        )
        db_session.add(new_user)
        db_session.commit()
        return True, f"User with email {form.email.data} has been created"
