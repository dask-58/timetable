import datetime
from collections import defaultdict

class TimeSlot:
    def __init__(self, day: str, start_time: datetime.time, end_time: datetime.time, slot_type: str = "Regular"):
        self.day = day
        self.start_time = start_time
        self.end_time = end_time
        self.slot_type = slot_type

    def duration_hours(self) -> float:
        start_dt = datetime.datetime.combine(datetime.date.today(), self.start_time)
        end_dt = datetime.datetime.combine(datetime.date.today(), self.end_time)
        return (end_dt - start_dt).total_seconds() / 3600

    def __str__(self) -> str:
        return f"{self.day} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    def overlaps(self, other) -> bool:
        if self.day != other.day:
            return False
        return self.start_time < other.end_time and self.end_time > other.start_time

class Room:
    def __init__(self, room_id: str, room_type: str, capacity: int):
        self.room_id = room_id
        self.room_type = room_type
        self.capacity = capacity

    def __str__(self) -> str:
        return f"{self.room_id} ({self.room_type}, capacity: {self.capacity})"

class Course:
    def __init__(self, course_id: str, course_name: str, professor_id: str, total_students: int,
                 num_lectures: int, num_labs: int, num_tutorials: int, fixed_classroom: str = None):
        self.course_id = course_id
        self.course_name = course_name
        self.professor_id = professor_id
        self.total_students = total_students
        self.num_lectures = num_lectures
        self.num_labs = num_labs
        self.num_tutorials = num_tutorials
        self.fixed_classroom = fixed_classroom

    def total_sessions(self) -> int:
        return self.num_lectures + self.num_labs + self.num_tutorials

    def __str__(self) -> str:
        return f"{self.course_id}: {self.course_name}, Students: {self.total_students}"

class Session:
    def __init__(self, course: Course, session_type: str, room: Room, time_slot: TimeSlot, session_id: int):
        self.course = course
        self.session_type = session_type
        self.room = room
        self.time_slot = time_slot
        self.session_id = session_id

    def __str__(self) -> str:
        suffix = {"Lecture": "L", "Tutorial": "T", "Lab": "P"}.get(self.session_type, "")
        return f"{self.course.course_id} ({suffix})"

class Timetable:
    def __init__(self):
        self.sessions = []
        self.course_day_sessions = defaultdict(lambda: defaultdict(list))
        self.room_timeslot_map = {}
        self.professor_timeslot_map = {}
        self.lab_days = defaultdict(set)

    def add_session(self, session: Session) -> None:
        self.sessions.append(session)
        self.course_day_sessions[session.course.course_id][session.time_slot.day].append(session)
        key = (session.room.room_id, session.time_slot)
        self.room_timeslot_map[key] = session
        prof_key = (session.course.professor_id, session.time_slot)
        self.professor_timeslot_map[prof_key] = session
        if session.session_type == "Lab":
            self.lab_days[session.time_slot.day].add(session.course.course_id)

    def remove_last_session(self) -> Session:
        if not self.sessions:
            return None
        session = self.sessions.pop()
        self.course_day_sessions[session.course.course_id][session.time_slot.day].remove(session)
        if not self.course_day_sessions[session.course.course_id][session.time_slot.day]:
            del self.course_day_sessions[session.course.course_id][session.time_slot.day]
        key = (session.room.room_id, session.time_slot)
        if key in self.room_timeslot_map:
            del self.room_timeslot_map[key]
        prof_key = (session.course.professor_id, session.time_slot)
        if prof_key in self.professor_timeslot_map:
            del self.professor_timeslot_map[prof_key]
        if session.session_type == "Lab":
            self.lab_days[session.time_slot.day].discard(session.course.course_id)
        return session

    def is_room_available(self, room: Room, time_slot: TimeSlot) -> bool:
        if (room.room_id, time_slot) in self.room_timeslot_map:
            return False
        for r, slot in self.room_timeslot_map.keys():
            if r == room.room_id and time_slot.overlaps(slot):
                return False
        return True

    def is_professor_available(self, professor_id: str, time_slot: TimeSlot) -> bool:
        if (professor_id, time_slot) in self.professor_timeslot_map:
            return False
        for p, slot in self.professor_timeslot_map.keys():
            if p == professor_id and time_slot.overlaps(slot):
                return False
        return True

    def count_session_type_on_day(self, course_id: str, session_type: str, day: str) -> int:
        return sum(1 for session in self.course_day_sessions[course_id].get(day, []) if session.session_type == session_type)

    def count_sessions_on_day(self, course_id: str, day: str) -> int:
        return len(self.course_day_sessions[course_id].get(day, []))
