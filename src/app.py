from flask import Flask, request, render_template_string, redirect, flash
import pandas as pd
import random
import datetime
from models import Room, Course, TimeSlot
from generator import TimetableGenerator

app = Flask(__name__)
app.secret_key = "secret_key_for_demo"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("No file part in the request.")
            return redirect(request.url)
        file = request.files["csv_file"]
        semester = request.form.get("semester", "")
        if file.filename == "":
            flash("No selected file.")
            return redirect(request.url)
        try:
            df = pd.read_csv(file)
            df.columns = ["Course Code", "Course Name", "L", "T", "P", "S", "C", "Faculty", "Classroom"]
        except Exception as e:
            flash(f"Error reading CSV: {e}")
            return redirect(request.url)

        rooms = []
        for classroom in df["Classroom"].unique():
            if pd.notna(classroom):
                rooms.append(Room(classroom, "Classroom", 60))
        rooms.extend([
            Room("L107", "LabRoom", 40),
            Room("L106", "LabRoom", 40)
        ])

        courses = []
        course_info = {}
        for _, row in df.iterrows():
            try:
                L = int(float(row["L"]))
                T = int(float(row["T"]))
                P = int(float(row["P"]))
            except (ValueError, TypeError) as e:
                print(f"Error parsing L, T, P for {row['Course Code']}: {e}")
                continue
            num_lectures = int(L / 1.5)
            num_tutorials = T
            num_labs = P // 2
            course = Course(
                course_id=row["Course Code"],
                course_name=row["Course Name"],
                professor_id=row["Faculty"],
                total_students=60,
                num_lectures=num_lectures,
                num_labs=num_labs,
                num_tutorials=num_tutorials,
                fixed_classroom=row["Classroom"] if pd.notna(row["Classroom"]) else None
            )
            courses.append(course)
            course_info[course.course_id] = {"faculty": course.professor_id,
                                               "classroom": course.fixed_classroom or "Not Assigned"}

        generator = TimetableGenerator()
        timetable = generator.generate_timetable(courses, rooms)
        generator.validate_timetable(timetable, courses, rooms)

        base_slots = [f"{h:02d}:{m:02d}-{h + (m + 30) // 60:02d}:{(m + 30) % 60:02d}" for h in range(9, 17) for m in [0, 30]]
        slot_count = len(base_slots)
        timetable_grid = {day: ["" for _ in range(slot_count)] for day in generator.working_days}
        for day in generator.working_days:
            for i in range(slot_count):
                start_str, end_str = base_slots[i].split("-")
                start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.datetime.strptime(end_str, "%H:%M").time()
                slot = TimeSlot(day, start_time, end_time)
                for session in timetable.sessions:
                    if session.time_slot.day == day and session.time_slot.overlaps(slot):
                        suffix = {"Lecture": "L", "Tutorial": "T", "Lab": "P"}.get(session.session_type, "")
                        timetable_grid[day][i] = f"{session.course.course_id} ({suffix})"
                for break_name, break_start, break_end in generator.fixed_break_slots:
                    break_slot = TimeSlot(day, break_start, break_end)
                    if slot.overlaps(break_slot):
                        timetable_grid[day][i] = break_name
                snack_slot = TimeSlot(day, generator.optional_snack_slot[1], generator.optional_snack_slot[2])
                if slot.overlaps(snack_slot) and any(s.session_type == "Snacks" and s.time_slot.day == day for s in timetable.sessions):
                    timetable_grid[day][i] = "Snacks"

        distinct_colors = ["#FF6347", "#4682B4", "#32CD32", "#FFD700", "#6A5ACD",
                           "#FF69B4", "#00CED1", "#FFA500", "#20B2AA", "#DAA520"]
        course_codes = df["Course Code"].unique()
        course_colors = {course: distinct_colors[i % len(distinct_colors)] for i, course in enumerate(course_codes)}

        semester_text = f"Semester {semester}"
        timetable_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>IIIT Dharwad Timetable - Semester IV</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: 'Inter', sans-serif;
                }
                
                body {
                    background-color: #f5f5f7;
                    padding: 2rem;
                    color: #1d1d1f;
                }

                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 2rem;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                }

                h2, h3 {
                    color: #1d1d1f;
                    margin-bottom: 1rem;
                }

                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 2rem;
                }

                .export-btn {
                    background-color: #007AFF;
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: background-color 0.2s;
                }

                .export-btn:hover {
                    background-color: #0056b3;
                }

                .timetable-container {
                    overflow-x: auto;
                    margin-bottom: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }

                table {
                    border-collapse: collapse;
                    width: 100%;
                    background-color: white;
                }

                th, td {
                    border: 1px solid #e0e0e0;
                    padding: 8px 4px;
                    text-align: center;
                    font-size: 0.85rem;
                    white-space: nowrap;
                }

                th {
                    background-color: #f8f9fa;
                    font-weight: 600;
                    color: #1d1d1f;
                }

                .break {
                    background-color: #FFE4E1;
                    color: #FF6B6B;
                    font-weight: 500;
                }

                .lunch {
                    background-color: #E8F5E9;
                    color: #2E7D32;
                    font-weight: 500;
                }

                .legend {
                    background-color: white;
                    padding: 1.5rem;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                    margin-top: 2rem;
                }

                .legend h3 {
                    margin-bottom: 1rem;
                    font-size: 1.1rem;
                    color: #1d1d1f;
                }

                .legend-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 1rem;
                }

                .legend-item {
                    display: flex;
                    align-items: center;
                    padding: 0.5rem;
                    border-radius: 6px;
                    background-color: #f8f9fa;
                }

                .color-box {
                    width: 16px;
                    height: 16px;
                    margin-right: 12px;
                    border-radius: 4px;
                    border: 1px solid rgba(0,0,0,0.1);
                }

                .course-info {
                    font-size: 0.9rem;
                }

                .course-code {
                    font-weight: 600;
                    margin-right: 8px;
                }

                @media (max-width: 768px) {
                    body {
                        padding: 1rem;
                    }
                    
                    .container {
                        padding: 1rem;
                    }
                    
                    .header {
                        flex-direction: column;
                        gap: 1rem;
                    }
                    
                    th, td {
                        padding: 8px;
                        font-size: 0.8rem;
                    }
                }
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h2>IIIT Dharwad Timetable</h2>
                        <h3>{{ semester_text }} (Dec 2024 - Apr 2025)</h3>
                        <p>Section A - Roll No 23BCS001 to 23BCS070</p>
                    </div>
                    <button class="export-btn" onclick="exportToExcel()">
                        Export to Excel
                    </button>
                </div>

                <div class="timetable-container">
                    <table id="timetable">
                        <tr>
                            <th>Time/Day</th>
                            {% for slot in base_slots %}
                                <th>{{ slot }}</th>
                            {% endfor %}
                        </tr>
                        {% for day in working_days %}
                        <tr>
                            <td><strong>{{ day }}</strong></td>
                            {% for i in range(slot_count) %}
                                {% set cell_content = timetable_grid[day][i] %}
                                {% if cell_content in ["Morning Break", "Lunch", "Snacks"] %}
                                    {% set class_name = "break" if cell_content in ["Morning Break", "Snacks"] else "lunch" %}
                                    <td class="{{ class_name }}">{{ cell_content }}</td>
                                {% else %}
                                    {% set color = course_colors.get(cell_content.split(' ')[0], "#FFFFFF") %}
                                    <td style="background-color: {{ color }}20; color: {{ color }}; font-weight: 500">
                                        {{ cell_content }}
                                    </td>
                                {% endif %}
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </table>
                </div>

                <div class="legend">
                    <h3>Course Information</h3>
                    <div class="legend-grid">
                        {% for course, info in course_info.items() %}
                            <div class="legend-item">
                                <span class="color-box" style="background-color: {{ course_colors.get(course, '#FFFFFF') }};"></span>
                                <div class="course-info">
                                    <span class="course-code">{{ course }}</span>
                                    <span>{{ info.faculty }} | {{ info.classroom }}</span>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <script>
                function exportToExcel() {
                    // ... existing export code ...
                }
            </script>
        </body>
        </html>
        """
        return render_template_string(timetable_template,
                                      semester_text=semester_text,
                                      base_slots=base_slots,
                                      working_days=generator.working_days,
                                      slot_count=slot_count,
                                      timetable_grid=timetable_grid,
                                      course_codes=course_codes,
                                      course_colors=course_colors,
                                      course_info=course_info)
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload Timetable CSV</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Inter', sans-serif;
            }
            
            body {
                background-color: #f5f5f7;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
            }

            .upload-container {
                background-color: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                width: 100%;
                max-width: 500px;
                text-align: center;
            }

            h2 {
                color: #1d1d1f;
                margin-bottom: 1.5rem;
                font-size: 1.8rem;
            }

            .file-input-container {
                background-color: #f8f9fa;
                padding: 2rem;
                border-radius: 8px;
                border: 2px dashed #dee2e6;
                margin-bottom: 1.5rem;
                cursor: pointer;
                transition: border-color 0.2s;
            }

            .file-input-container:hover {
                border-color: #007AFF;
            }

            .file-input-container p {
                color: #6c757d;
                margin-bottom: 1rem;
            }

            input[type="file"] {
                display: none;
            }

            .select-file-btn {
                background-color: #e9ecef;
                color: #495057;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                border: none;
                cursor: pointer;
                font-size: 0.9rem;
                transition: background-color 0.2s;
            }

            .select-file-btn:hover {
                background-color: #dee2e6;
            }

            .semester-select {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-size: 1rem;
                color: #495057;
            }

            .submit-btn {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 500;
                width: 100%;
                font-size: 1rem;
                transition: background-color 0.2s;
            }

            .submit-btn:hover {
                background-color: #0056b3;
            }

            .selected-file {
                margin-top: 1rem;
                color: #007AFF;
                font-weight: 500;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="upload-container">
            <h2>Generate Timetable</h2>
            <form method="POST" enctype="multipart/form-data">
                <select name="semester" class="semester-select" required>
                    <option value="">Select Semester</option>
                    <option value="I">Semester I</option>
                    <option value="II">Semester II</option>
                    <option value="III">Semester III</option>
                    <option value="IV">Semester IV</option>
                    <option value="V">Semester V</option>
                    <option value="VI">Semester VI</option>
                    <option value="VII">Semester VII</option>
                    <option value="VIII">Semester VIII</option>
                </select>
                <div class="file-input-container" onclick="document.getElementById('csv_file').click()">
                    <p>Click to upload your CSV file</p>
                    <button type="button" class="select-file-btn">Select File</button>
                    <div id="selected-file" class="selected-file"></div>
                </div>
                <input type="file" name="csv_file" id="csv_file" accept=".csv" required>
                <button type="submit" class="submit-btn">Generate Timetable</button>
            </form>
        </div>
        <script>
            document.getElementById('csv_file').addEventListener('change', function(e) {
                const fileName = e.target.files[0]?.name;
                const selectedFile = document.getElementById('selected-file');
                if (fileName) {
                    selectedFile.textContent = fileName;
                    selectedFile.style.display = 'block';
                } else {
                    selectedFile.style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """)
    
if __name__ == "__main__":
    random.seed(42)
    app.run(debug=True, port=5002)
