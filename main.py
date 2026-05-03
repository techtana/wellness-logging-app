
from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.config import DB_URI, GW_URL, PROJECT_NAME, USER_SESSION
import requests

# Import Blueprints
from funcs.create_questionaire import get_most_recent_activity
from funcs.make_recommendation import make_recommendation
from funcs.create_profile import use_llm_1

def create_app():
    app = Flask(__name__)
    

    # Set up SQLAlchemy engine and sessionmaker
    engine = create_engine(DB_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


    @app.route("/", methods=["GET"])
    def index():
        return render_template("directory.html")


    @app.route("/user", methods=["GET"])
    def user(uid='test'):
        with SessionLocal() as session:
            prev_rec = get_most_recent_activity(session, uid)
            # prev_rec = {"uid": uid, "item": activity, "date": date}
        return render_template("user.html", uid=uid, prev_rec=prev_rec)
    

    @app.route('/submit', methods=['POST'])
    def submit():
        data = request.get_json()
        # split data into feedback and current_state
        feedback = {
            'user_id': data.get("user_id", {}),
            'feedback': data.get("prev_recommendations", {})
        }
        responses = {
            'user_id': data.get("user_id", {}),
            'response': data.get("responses", {})
        }

        # TODO @Nimesh: send response to llm #1
        prompt = use_llm_1(responses)


        # TODO @Tech: send feedback and llm #1 response to llm #2
        _count = 0
        response = requests.post(
            f"{GW_URL}/hackathon/{PROJECT_NAME}/batch/{USER_SESSION}", 
            json = {
                "batch_count": 1,
                "events": [
                    { "event": "abstract interest",
                        "properties": {
                            "organization_id": "fly_finder",
                            "visitor_id": "6ee0e958-adb0-49b4-8415-31556bef71e9",
                            "session_id": "d9a510fb-10a9-4c76-981e-9988559142f8",
                            "id": "02J0",
                            "weight": 4
                        }
                    },
                ],
                "page": _count,
                "search_prompt": prompt
                }
        )


        # Here you would process the input and generate recommendations
        return render_template("user.html", data=response)
    
    @app.route('/test_result/<case>', methods=['GET'])
    def test_result(case):
        return render_template(f"test_result_{case}.html")
        
        
    return app


if __name__ == "__main__":
    app = create_app()
    port = 5005
    app.run(debug=True, port=port)