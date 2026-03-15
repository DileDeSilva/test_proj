from db import Database


class PasswordValidator:
    def __init__(self):
        self.special_symbols = ['$', '@', '#', '%', '!', '^', '&']

    def is_valid(self, password):
        val = True

        if len(password) < 8:
            val = False
        if len(password) > 15:
            val = False
        if not any(char.isdigit() for char in password):
            val = False
        if not any(char.isupper() for char in password):
            val = False
        if not any(char.islower() for char in password):
            val = False
        if not any(char in self.special_symbols for char in password):
            val = False

        return val


class UserService:
    def __init__(self, db=None, password_validator=None):
        self.db = db if db else Database()
        self.password_validator = password_validator if password_validator else PasswordValidator()

    def register_user(self, username, password):
        if not self.password_validator.is_valid(password):
            return "Invalid password"

        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            conn.close()
            return "Username already exists"

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, password),
        )
        conn.commit()
        conn.close()
        return "Registration successful"

    def save_basic_details(self, gender, email, age):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
                INSERT INTO userdetails (gender, email, age)
                VALUES (%s, %s, %s)
            """,
            (gender, email, age),
        )
        userdetails_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return "Details saved successfully", userdetails_id

    def login_user(self, username, password):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT username FROM users WHERE username = %s AND password = %s",
            (username, password),
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            return f"Welcome {username}", True
        return "Invalid username or password", False

    def save_additional_details(self, userdetails_id, fullname, contactNo, address, reference_no):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE userdetails
            SET fullname = %s, contactNo = %s, address = %s, reference_no = %s
            WHERE ID = %s
            """,
            (fullname, contactNo, address, reference_no, userdetails_id),
        )

        conn.commit()
        conn.close()
        return "Additional details saved successfully"


class QuestionnaireService:
    def __init__(self, db=None):
        self.db = db if db else Database()

    def save_questionnaire_results(self, user_id, result):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO questionnaire_results
            (user_id, depression_score, depression_level, anxiety_score, anxiety_level,
             stress_score, stress_level, overall_level, recommendations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                result['depression_score'],
                result['depression_level'],
                result['anxiety_score'],
                result['anxiety_level'],
                result['stress_score'],
                result['stress_level'],
                result['level'],
                result['recommendations'],
            ),
        )

        conn.commit()
        result_id = cursor.lastrowid
        conn.close()

        return result_id

    def questionnaire(self, scores):
        depression_indices = [0, 1, 2, 3, 4, 5, 6]
        anxiety_indices = [7, 8, 9, 10, 11, 12, 13]
        stress_indices = [14, 15, 16, 17, 18, 19, 20]

        severity_cutoffs = {
            "depression": [
                (9, "Normal"),
                (13, "Mild"),
                (20, "Moderate"),
                (27, "Severe"),
                (float('inf'), "Extremely Severe"),
            ],
            "anxiety": [
                (7, "Normal"),
                (9, "Mild"),
                (14, "Moderate"),
                (19, "Severe"),
                (float('inf'), "Extremely Severe"),
            ],
            "stress": [
                (14, "Normal"),
                (18, "Mild"),
                (25, "Moderate"),
                (33, "Severe"),
                (float('inf'), "Extremely Severe"),
            ],
        }

        depression_score = sum(scores[i] for i in depression_indices) * 2
        anxiety_score = sum(scores[i] for i in anxiety_indices) * 2
        stress_score = sum(scores[i] for i in stress_indices) * 2

        def level_for(score, cutoffs):
            for cutoff, level in cutoffs:
                if score <= cutoff:
                    return level
            return "Unknown"

        depression_level = level_for(depression_score, severity_cutoffs["depression"])
        anxiety_level = level_for(anxiety_score, severity_cutoffs["anxiety"])
        stress_level = level_for(stress_score, severity_cutoffs["stress"])

        if depression_score >= anxiety_score and depression_score >= stress_score:
            level_of_user = "level 3"
        elif anxiety_score >= depression_score and anxiety_score >= stress_score:
            level_of_user = "level 2"
        else:
            level_of_user = "level 1"

        if level_of_user == "level 3":
            recommendations = self.stage3()
        elif level_of_user == "level 2":
            recommendations = self.stage2()
        else:
            recommendations = self.stage1()

        return {
            'depression_score': depression_score,
            'depression_level': depression_level,
            'anxiety_score': anxiety_score,
            'anxiety_level': anxiety_level,
            'stress_score': stress_score,
            'stress_level': stress_level,
            'level': level_of_user,
            'recommendations': recommendations,
        }

    def stage1(self):
        return """
    ### 1. Connect with other people
- Take time each day to be with your family
- Arrange a day out with friends you have not seen for a while
- Have lunch with a colleague
- Visit a friend or family member who needs support or company
- Make the most of technology to stay in touch

### 2. Be physically active
- Read about exercise such as running and aerobic exercises
- Improve your strength and flexibility
- Find activities you enjoy and make them a part of your life

### 3. Learn new skills
- Try learning to cook something new
- Take on a new responsibility at work
- Work on a DIY project
- Consider signing up for a course at a local college
- Try new hobbies that challenge you

### 4. Give to others
- Say thank you to someone
- Spend time with friends or relatives who need support
- Volunteer in your community

### 5. Pay attention to the present moment (mindfulness)
- Mindfulness can help you enjoy life more and understand yourself better
- It can positively change the way you feel about life

### 6. Helpful Video Resources
- [ Click here to watch video 1 ](https://www.youtube.com/watch?v=6ijg6tpyxXg&utm_source=chatgpt.com)
- [ Click here to watch video 2 ](https://www.youtube.com/watch?v=hJbRpHZr_d0&utm_source=chatgpt.com)
- [ Click here to watch video 3 ](https://www.youtube.com/watch?v=tYddPTEfS_8&utm_source=chatgpt.com)
- [ Click here to watch video 4 ](https://www.youtube.com/watch?v=sTANio_2E0Q&utm_source=chatgpt.com)
- [ Click here to watch video 5 ](https://www.youtube.com/watch?v=Pv-baSmxcyY&utm_source=chatgpt.com)

### 6. Helpful  Music
- [ Click here to watch video 1 ](http://www.youtube.com/watch?v=jfKfPfyJRdk&utm_source=chatgpt.com)
- [ Click here to watch video 2 ](http://www.youtube.com/watch?v=o8GrqUSdzi0&utm_source=chatgpt.com)
- [ Click here to watch video 3 ](http://www.youtube.com/watch?v=BrFu8WwyYHQ&utm_source=chatgpt.com)
"""

    def stage2(self):
        return """
    ### Self-help therapies
    Self-help therapies are psychological therapies that you can do in your own time to help with problems like stress, anxiety and depression.

    ### Self-help books
    - Reading Well books (available free from your local library)
    - Overcoming website offers books and apps covering more than 30 common mental health problems

    ### Online resources
    - Side by Side forum at Mind: a safe, supportive online community
    - Blogs and stories at Mind: people share their struggles with mental health
    - Relaxation videos and audio guides
    - NHS audio guides on anxiety, depression and more

    ### 6. Helpful Video Resources
    - [ Click here to watch video 1 ](https://www.youtube.com/watch?v=hJbRpHZr_d0&utm_source=chatgpt.com)
    - [ Click here to watch video 2 ](https://www.youtube.com/watch?v=sTANio_2E0Q&utm_source=chatgpt.com)
    - [ Click here to watch video 3 ](https://www.youtube.com/watch?v=Pv-baSmxcyY&utm_source=chatgpt.com)
    - [ Click here to watch video 4 ](https://www.youtube.com/watch?v=2IJUD-e14FY&utm_source=chatgpt.com)
    - [ Click here to watch video 5 ](https://www.youtube.com/watch?v=SNqYG95j_UQ&utm_source=chatgpt.com)

    """

    def stage3(self):
        return """
    ### Self-help techniques for severe symptoms

    #### Learning about your condition
    Learn more about your mental health condition to increase understanding and acceptance.

    #### Relaxation and breathing exercises
    - Practice deep, slow breaths (e.g., breathe in for 5, hold for 3, release for 7)
    - Spend time with pets, take baths, or listen to music

    #### Mindfulness
    Focus on the present moment using meditation, yoga, or the five senses.

    #### Exercise
    Engage in around 30 minutes of exercise per day (walking, swimming, running, etc.).

    #### Social activities
    Form and maintain a support system with friends and family.

    #### Diet
    Eat a healthy diet high in fish, fruits, vegetables, and unprocessed foods.

    #### Sleep hygiene
    - Go to bed and wake up at the same time every day
    - Avoid caffeine and screens before bed
    - Sleep in a dark and quiet room

    #### When to seek professional help
    You should seek help if symptoms become more severe or self-help techniques don't work. Consult with your doctor about medications and psychotherapy options.
    """


_db = Database()
_user_service = UserService(db=_db)
_questionnaire_service = QuestionnaireService(db=_db)


# Backward-compatible functions (old UI imports still work)
def password_check(password):
    return _user_service.password_validator.is_valid(password)


def register_user(username, password):
    return _user_service.register_user(username, password)


def details_user(gender, email, age):
    return _user_service.save_basic_details(gender, email, age)


def login_user(username, password):
    return _user_service.login_user(username, password)


def save_questionnaire_results(user_id, result):
    return _questionnaire_service.save_questionnaire_results(user_id, result)


def save_additional_details(userdetails_id, fullname, contactNo, address, reference_no):
    return _user_service.save_additional_details(userdetails_id, fullname, contactNo, address, reference_no)


def questionnaire(scores):
    return _questionnaire_service.questionnaire(scores)