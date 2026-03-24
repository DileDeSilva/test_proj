import base64
import os
import traceback
from pathlib import Path

import streamlit as st

# try:
#     from dotenv import load_dotenv
#     _env_path = Path(__file__).resolve().parent / ".env"
#     load_dotenv(_env_path)
# except ImportError:
#     pass
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from db import Database
from functions import QuestionnaireService, UserService

# Minimal valid PDF (used only if data.pdf is missing so the chat can still run)
_MINIMAL_PDF_B64 = (
    "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0tpZHMgWzMgMCBSXS9Db3VudCAxPj4KZW5kb2JqCjMgMCBvYmoKPDwvVHlwZS9QYWdlL01lZGlhQm94IFswIDAgMyAzXS9QYXJlbnQgMiAwIFI+PgplbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDEwMSAwMDAwMCBuIAp0cmFpbGVyCjw8L1NpemUgNC9Sb290IDEgMCBSPj4Kc3RhcnR4cmVmCjE3OAolJUVPRg=="
)


class MentalHealthAppUI:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService(db=self.db)
        self.questionnaire_service = QuestionnaireService(db=self.db)
        # Same folder as this script — works no matter what folder you run streamlit from
        self.chatbot_pdf_path = Path(__file__).resolve().parent / "data.pdf"

    def _get_chatbot_pdf_bytes(self):
        """Prefer data.pdf on disk; otherwise use embedded minimal PDF."""
        if self.chatbot_pdf_path.exists():
            return self.chatbot_pdf_path.read_bytes(), str(self.chatbot_pdf_path.name)
        return base64.b64decode(_MINIMAL_PDF_B64), "built-in placeholder (add data.pdf next to UI.py for your content)"

    def add_bg_image(self):
        with open("cute-furry-cat-outdoors.jpg", "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()

        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpeg;base64,{encoded}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    def init_state(self):
        if 'registered' not in st.session_state:
            st.session_state.registered = False
        if 'details_saved' not in st.session_state:
            st.session_state.details_saved = False
        if 'login_successfully' not in st.session_state:
            st.session_state.login_successfully = False
        if 'saved_additional_details' not in st.session_state:
            st.session_state.saved_additional_details = False
        if 'questionnaire_result' not in st.session_state:
            st.session_state.questionnaire_result = None
        if 'userdetails_id' not in st.session_state:
            st.session_state.userdetails_id = None
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "main"
        if 'chatbot_messages' not in st.session_state:
            st.session_state.chatbot_messages = []

    def show_register_form(self):
        st.subheader("Registration Form")

        username = st.text_input("Username", key="reg_username")
        password = st.text_input("Password", type="password", key="reg_password")
        st.write(
            "(password Length should be at least 8, Length should not be greater than 15, "
            "should have at least one number,uppercase letter and lowercase letter and "
            "should have at least one of the symbols $@#%!^&)"
        )

        if st.button("Register"):
            if username and password:
                result = self.user_service.register_user(username.strip(), password.strip())
                if result == "Registration successful":
                    st.success(result)
                    st.session_state.registered = True
                else:
                    st.error(result)
            else:
                st.warning("Please fill all fields")

        if st.session_state.registered and st.session_state.current_page == "main":
            st.write("Now fill the details form.")
            if st.button("Continue to Details Form"):
                st.session_state.current_page = "details"
                st.rerun()

    def show_details_form(self):
        st.subheader("Details Form")

        gender = st.radio("Select Gender:", ["Male", "Female"], key="gender")
        email = st.text_input("Enter your email address:", key="email")
        age = st.number_input(
            "Enter age:",
            min_value=1,
            max_value=120,
            step=1,
            value=None,
            format="%d",
            key="age",
        )

        if st.button("Save Details"):
            if age is None:
                st.error("Please enter your age correctly.")
            if not email:
                st.error("Please enter your email")
            elif age is not None and (age < 1 or age > 120):
                st.error("Age must be between 1 and 120")
            elif email and ('@' not in email or '.' not in email):
                st.error("Invalid email format")
            else:
                result, userdetails_id = self.user_service.save_basic_details(gender, email, age)
                if "saved" in result:
                    st.success(result)
                    st.session_state.details_saved = True
                    st.session_state.userdetails_id = userdetails_id
                else:
                    st.error(result)

        if st.session_state.details_saved and st.session_state.current_page == "details":
            st.write("You can login now.")
            if st.button("Continue to Login"):
                st.session_state.current_page = "login"
                st.rerun()

    def show_login_form(self):
        st.subheader("Login Form")

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            if username and password:
                result, success = self.user_service.login_user(username.strip(), password.strip())
                if success:
                    st.success(result)
                    st.session_state.login_successfully = True
                    st.session_state.username = username.strip()
                else:
                    st.error(result)
            else:
                st.error("Please enter username and password")

        if st.session_state.login_successfully:
            st.write("Answer the questionnaire.")
            if st.button("Continue to Questionnaire"):
                st.session_state.current_page = "questionnaire"
                st.rerun()

    def show_questionnaire(self):
        st.subheader("DASS-21 Mental Health Questionnaire")

        st.write("**Answer the following 21 questions with a score from 0 to 3:**")
        st.info(
            """
            - **0** = Did not apply to me at all
            - **1** = Applied to me to some degree, or some of the time
            - **2** = Applied to me to a considerable degree, or a good part of time
            - **3** = Applied to me very much, or most of the time
            """
        )

        scores = []
        questions = self.db.get_questions()
        for i, question in enumerate(questions, 1):
            st.write(f"**Q{i}. {question}**")
            score = st.radio(
                f"Your score for Q{i}:",
                options=[0, 1, 2, 3],
                key=f"q{i}",
                horizontal=True,
                index=None,
            )
            scores.append(score)

        if st.button("Submit Questionnaire"):
            if None in scores:
                st.error("Please answer all 21 questions before submitting")
                return

            result = self.questionnaire_service.questionnaire(scores)
            self.questionnaire_service.save_questionnaire_results(None, result)

            st.session_state.questionnaire_result = result
            st.session_state.chatbot_messages = []

            st.success("Questionnaire completed!")

        saved_result = st.session_state.questionnaire_result
        if saved_result:
            st.write("---")
            st.subheader("DASS-21 Evaluation Results")
            st.write(f"\n**Your level is: {saved_result['level']}**")

            st.write("---")
            st.subheader("Recommendations")
            st.write(saved_result['recommendations'])

            self.show_genai_pdf_chatbot()

            if saved_result['level'] == "level 3":
                self.show_level3_support()
            else:
                self.show_exit_block()

    def generate_pdf_chat_response(self, question, pdf_bytes, api_key, chat_history):
        if genai is None or types is None:
            raise RuntimeError("google-genai is not installed. Run: pip install google-genai")

        # Send recent conversation to keep context for multi-question chats.
        history_lines = []
        for message in chat_history[-10:]:
            role = "User" if message.get("role") == "user" else "Assistant"
            content = message.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

        prompt = (
            "Answer based on the reference document provided. If the answer is not in the document, "
            "say that clearly.\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Current user question: {question}"
        )

        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type='application/pdf',
                ),
                prompt,
            ],
        )
        text = self._extract_gemini_text(response)
        return text if text else "I could not generate a response."

    def _extract_gemini_text(self, response):
        """Handle different response shapes from google-genai."""
        if response is None:
            return None
        t = getattr(response, "text", None)
        if t:
            return t
        try:
            candidates = getattr(response, "candidates", None) or []
            parts_out = []
            for cand in candidates:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", None) or []:
                    ptext = getattr(part, "text", None)
                    if ptext:
                        parts_out.append(ptext)
            return "\n".join(parts_out) if parts_out else None
        except Exception:
            return None

    def _get_gemini_api_key(self):
        """Load API key from Streamlit secrets (developer setup only)."""
        try:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
        except Exception:
            pass
        return ""

    def show_genai_pdf_chatbot(self):
        st.write("---")
        st.subheader("Chat assistant")
        st.caption("Ask questions below. Answers use our built-in information.")

        has_genai = genai is not None and types is not None
        api_key = self._get_gemini_api_key()
        pdf_bytes, pdf_source = self._get_chatbot_pdf_bytes()

        with st.expander("Setup status (administrator — fix if chat does not work)", expanded=not (has_genai and api_key)):
            st.markdown(
                f"- **google-genai package:** {'OK' if has_genai else 'MISSING — run: `pip install google-genai`'}\n"
                f"- **GEMINI_API_KEY:** {'loaded' if api_key else 'NOT SET — create `.streamlit/secrets.toml` with `GEMINI_API_KEY=your_key`, then restart terminal'}\n"
                f"- **PDF source:** {pdf_source}"
            )

        if not has_genai:
            st.warning(
                "Install the Gemini library, then refresh the page:  \n"
                "`pip install google-genai`"
            )
            return

        if not api_key:
            st.warning(
                "The API key is not loaded. Add **`.streamlit/secrets.toml`** in this project folder with:\n\n"
                "`GEMINI_API_KEY=your_key_here`\n\n"
                "Then **close and reopen** the terminal and run Streamlit again."
            )
            return

        # PDF always available (file or embedded fallback)

        for message in st.session_state.chatbot_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Type your question here…")
        if not user_input:
            return

        st.session_state.chatbot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        try:
            bot_response = self.generate_pdf_chat_response(
                user_input,
                pdf_bytes,
                api_key,
                st.session_state.chatbot_messages,
            )
        except Exception:
            if os.environ.get("STREAMLIT_DEBUG_CHAT", "").lower() in ("1", "true", "yes"):
                bot_response = f"Debug error:\n```\n{traceback.format_exc()}\n```"
            else:
                bot_response = (
                    "Sorry, something went wrong. Please try again in a moment."
                )

        st.session_state.chatbot_messages.append({"role": "assistant", "content": bot_response})
        with st.chat_message("assistant"):
            st.markdown(bot_response)

    def show_level3_support(self):
        st.write("---")
        st.subheader("Access Professional Support")

        st.info(
            """
            **Why is there a fee?**

            To connect you with qualified mental health professionals and ensure quality service,
            a nominal consultation fee is required.
            """
        )

        st.markdown(
            """
            ### Payment Details

            **Consultation Fee:** LKR 2,500.00

            **What's Included:**
            - Professional mental health assessment review
            - Access to qualified professionals
            - One consultation session
            - Follow-up support coordination
            - Priority booking
            """
        )

        st.write("**Bank Transfer Details:**")
        st.code(
            """
            Bank Name: Commercial Bank of Ceylon
            Account Name: Mental Health Services (Pvt) Ltd
            Account Number: 1234567890
            Branch: Colombo 03
            """
        )

        fullname = st.text_input("Enter full name:", key="fullname")
        address = st.text_input("Enter address:", key="address")
        contactNo = st.text_input("Enter contact number:", key="contactNo")
        reference_no = st.text_input("Enter reference number:", key="reference_no")

        if st.button("Save Additional Details"):
            if fullname and contactNo and reference_no and address:
                self.user_service.save_additional_details(
                    st.session_state.username,
                    fullname,
                    contactNo,
                    address,
                    reference_no,
                )
                st.success("Additional details saved successfully")
                st.session_state.saved_additional_details = True
            else:
                st.warning("Please fill all fields")

        if st.session_state.saved_additional_details:
            st.write("---")
            st.subheader("We can connect you with the most appropriate professional.")
            professionals = self.db.get_professionals()
            for prof in professionals:
                pid, name, designation, specialization, district, contact_no = prof
                st.write(f"**{name}** - {designation}")
                st.write(f"- Specialization: {specialization}")
                st.write(f"- District: {district}")
                st.write(f"- Contact No: {contact_no}")
                st.write("---")

            self.show_exit_block()

    def show_exit_block(self):
        st.write("---")
        st.subheader("Exit Application")
        if st.button("Exit"):
            st.info("Thank you for using the Mental Health Application!")
            st.write("You can now close this browser tab.")
            st.stop()

    def run(self):
        self.add_bg_image()
        self.init_state()

        st.title("Mental Health Application")

        # Page-based flow: when on a specific step, show only that step (new page)
        if st.session_state.current_page == "details":
            if st.button("← Back to Home"):
                st.session_state.current_page = "main"
                st.rerun()
            st.write("---")
            self.show_details_form()
            return

        if st.session_state.current_page == "login":
            if st.button("← Back to Home"):
                st.session_state.current_page = "main"
                st.rerun()
            st.write("---")
            self.show_login_form()
            return

        if st.session_state.current_page == "questionnaire":
            # Only logged-in users can answer the questionnaire
            if not st.session_state.login_successfully:
                st.warning("You must register and login before you can fill the questionnaire.")
                st.write("Please register (if you are new) or login to continue.")
                if st.button("Go to Home"):
                    st.session_state.current_page = "main"
                    st.rerun()
                return
            if st.button("← Back to Home"):
                st.session_state.current_page = "main"
                st.rerun()
            st.write("---")
            self.show_questionnaire()
            return

        # Main page: only Register, Login, Exit (no Details or Questionnaire as direct options)
        choice = st.radio(
            "Select an option:",
            ["Register", "Login", "Exit"],
            horizontal=True,
        )

        if choice == "Register":
            self.show_register_form()

        elif choice == "Login":
            self.show_login_form()

        elif choice == "Exit":
            self.show_exit_block()


if __name__ == "__main__":
    MentalHealthAppUI().run()