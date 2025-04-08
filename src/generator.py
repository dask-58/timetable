import datetime
import random
import copy
from collections import defaultdict
from typing import List, Tuple
from models import TimeSlot, Room, Course, Session, Timetable

class TimetableGenerator:
    def __init__(self):
        self.working_days = ["MON", "TUE", "WED", "THU", "FRI"]
        self.fixed_break_slots = [
            ("Morning Break", datetime.time(10, 30), datetime.time(11, 0)),
            ("Lunch", datetime.time(13, 30), datetime.time(14, 30))
        ]
        self.optional_snack_slot = ("Snacks", datetime.time(16, 30), datetime.time(17, 0))
        self.working_hours = {"start": datetime.time(9, 0), "end": datetime.time(17, 0)}
        self.durations = {"Lecture": 1.5, "Lab": 2.0, "Tutorial": 1.0}
        self.max_backtrack_attempts = 2000
        self.backtrack_count = 0
        self.session_ids = defaultdict(lambda: {"Lecture": 0, "Tutorial": 0, "Lab": 0})

    def generate_time_slots(self) -> List[TimeSlot]:
        time_slots = []
        for day in self.working_days:
            for break_name, start, end in self.fixed_break_slots:
                time_slots.append(TimeSlot(day, start, end, break_name))
            current_time = self.working_hours["start"]
            while current_time < self.working_hours["end"]:
                for session_type, duration in self.durations.items():
                    duration_delta = datetime.timedelta(hours=duration)
                    end_time_dt = datetime.datetime.combine(datetime.date.today(), current_time) + duration_delta
                    end_time = end_time_dt.time()
                    if end_time <= self.working_hours["end"]:
                        slot = TimeSlot(day, current_time, end_time)
                        valid = True
                        for _, break_start, break_end in self.fixed_break_slots:
                            break_slot = TimeSlot(day, break_start, break_end)
                            if slot.overlaps(break_slot):
                                valid = False
                                break
                        if valid:
                            time_slots.append(slot)
                current_dt = datetime.datetime.combine(datetime.date.today(), current_time) + datetime.timedelta(minutes=30)
                current_time = current_dt.time()
        return time_slots

    def filter_time_slots(self, time_slots: List[TimeSlot], session_type: str) -> List[TimeSlot]:
        duration = self.durations[session_type]
        return [slot for slot in time_slots if slot.slot_type == "Regular" and abs(slot.duration_hours() - duration) < 0.01]

    def select_best_room(self, course: Course, session_type: str, available_rooms: List[Room]) -> Room:
        if not available_rooms:
            return None
        if course.fixed_classroom and session_type != "Lab":
            for room in available_rooms:
                if room.room_id == course.fixed_classroom:
                    return room
        if session_type == "Lab":
            lab_rooms = [room for room in available_rooms if room.room_type == "LabRoom"]
            if lab_rooms:
                suitable_labs = [r for r in lab_rooms if r.capacity >= course.total_students]
                return min(suitable_labs, key=lambda r: r.capacity) if suitable_labs else max(lab_rooms, key=lambda r: r.capacity)
        classrooms = [room for room in available_rooms if room.room_type == "Classroom"]
        if classrooms:
            suitable_classrooms = [r for r in classrooms if r.capacity >= course.total_students]
            return min(suitable_classrooms, key=lambda r: r.capacity) if suitable_classrooms else max(classrooms, key=lambda r: r.capacity)
        return min(available_rooms, key=lambda r: abs(r.capacity - course.total_students))
    # def select_best_room(self, course: Course, session_type: str, available_rooms: List[Room]) -> Room:
    #     if not available_rooms:
    #         return None
            

    #     if session_type == "Lab":
    #         lab_rooms = [room for room in available_rooms if room.room_type == "LabRoom"]
    #         if lab_rooms:
    #             suitable_labs = [r for r in lab_rooms if r.capacity >= course.total_students]
    #             return min(suitable_labs, key=lambda r: r.capacity) if suitable_labs else max(lab_rooms, key=lambda r: r.capacity)
                
    #     # Check fixed classroom for non-lab sessions
    #     if course.fixed_classroom and session_type != "Lab":
    #         for room in available_rooms:
    #             if room.room_id == course.fixed_classroom:
    #                 return room
                    
    #     # Default room selection logic
    #     classrooms = [room for room in available_rooms if room.room_type == "Classroom"]
    #     if classrooms:
    #         suitable_classrooms = [r for r in classrooms if r.capacity >= course.total_students]
    #         return min(suitable_classrooms, key=lambda r: r.capacity) if suitable_classrooms else max(classrooms, key=lambda r: r.capacity)
            
    #     return min(available_rooms, key=lambda r: abs(r.capacity - course.total_students))

    def get_available_rooms(self, rooms: List[Room], course: Course, session_type: str, time_slot: TimeSlot, timetable: Timetable) -> List[Room]:
        available = []
        for room in rooms:
            if not timetable.is_room_available(room, time_slot):
                continue
            if session_type == "Lab" and room.room_type != "LabRoom":
                continue
            if course.fixed_classroom and session_type != "Lab" and room.room_id != course.fixed_classroom:
                continue
            available.append(room)
        return available

    def assign_session(self, course: Course, session_type: str, available_time_slots: List[TimeSlot], rooms: List[Room], timetable: Timetable) -> bool:
        valid_slots = self.filter_time_slots(available_time_slots, session_type)
        random.shuffle(valid_slots)
        for time_slot in valid_slots:
            if not timetable.is_professor_available(course.professor_id, time_slot):
                continue
            if session_type == "Lab":
                day_idx = self.working_days.index(time_slot.day)
                prev_day = self.working_days[day_idx - 1] if day_idx > 0 else None
                next_day = self.working_days[day_idx + 1] if day_idx < len(self.working_days) - 1 else None
                if (prev_day and course.course_id in timetable.lab_days[prev_day]) or (next_day and course.course_id in timetable.lab_days[next_day]):
                    continue
            available = self.get_available_rooms(rooms, course, session_type, time_slot, timetable)
            if not available:
                continue
            best_room = self.select_best_room(course, session_type, available)
            if best_room:
                session_id = self.session_ids[course.course_id][session_type]
                session = Session(course, session_type, best_room, time_slot, session_id)
                timetable.add_session(session)
                self.session_ids[course.course_id][session_type] += 1
                available_time_slots.remove(time_slot)
                print(f"Scheduled {session_type} [ID:{session_id}] for {course.course_id} on {time_slot}")
                return True
        print(f"Failed to schedule {session_type} for {course.course_id}")
        return False

    def generate_timetable(self, courses: List[Course], rooms: List[Room]) -> Timetable:
        timetable = Timetable()
        all_time_slots = self.generate_time_slots()
        sorted_courses = sorted(courses, key=lambda c: (-c.num_labs, -c.total_sessions(), -c.total_students))
        assignment_stack = []
        for course in sorted_courses:
            available_time_slots = copy.deepcopy(all_time_slots)
            for session_type, count in [("Lab", course.num_labs), ("Lecture", course.num_lectures), ("Tutorial", course.num_tutorials)]:
                for _ in range(count):
                    if self.assign_session(course, session_type, available_time_slots, rooms, timetable):
                        assignment_stack.append((course, session_type))
                    else:
                        return self.backtrack(timetable, courses, rooms, assignment_stack)
        return timetable

    def backtrack(self, timetable: Timetable, courses: List[Course], rooms: List[Room], assignment_stack: List[Tuple]) -> Timetable:
        self.backtrack_count += 1
        if self.backtrack_count > self.max_backtrack_attempts:
            print(f"Warning: Maximum backtracking attempts ({self.max_backtrack_attempts}) reached.")
            return timetable
        session = timetable.remove_last_session()
        if not assignment_stack:
            print("Error: No more assignments to backtrack.")
            return timetable
        last_course, last_session_type = assignment_stack.pop()
        all_time_slots = self.generate_time_slots()
        if self.assign_session(last_course, last_session_type, all_time_slots, rooms, timetable):
            assignment_stack.append((last_course, last_session_type))
            return self.generate_timetable(courses, rooms)
        return self.backtrack(timetable, courses, rooms, assignment_stack)

    def validate_timetable(self, timetable: Timetable, courses: List[Course], rooms: List[Room]):
        all_time_slots = self.generate_time_slots()
        for course in courses:
            expected = {
                "Lecture": course.num_lectures,
                "Tutorial": course.num_tutorials,
                "Lab": course.num_labs
            }
            assigned = {
                "Lecture": sum(1 for s in timetable.sessions if s.course.course_id == course.course_id and s.session_type == "Lecture"),
                "Tutorial": sum(1 for s in timetable.sessions if s.course.course_id == course.course_id and s.session_type == "Tutorial"),
                "Lab": sum(1 for s in timetable.sessions if s.course.course_id == course.course_id and s.session_type == "Lab")
            }
            if assigned != expected:
                print(f"Validation Failed for {course.course_id}: Expected {expected}, Got {assigned}")
                avail_slots = copy.deepcopy(all_time_slots)
                for session_type in ["Lecture", "Tutorial", "Lab"]:
                    for _ in range(expected[session_type] - assigned[session_type]):
                        self.assign_session(course, session_type, avail_slots, rooms, timetable)
