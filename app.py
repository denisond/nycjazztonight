from flask import Flask, render_template
app = Flask(__name__)

from datetime import datetime
import pandas as pd


@app.route("/")
def home():
    try:
        schedule_df_temp = pd.read_csv('schedule.csv')
        schedule_df = schedule_df_temp.set_index([pd.to_datetime(schedule_df_temp['date']).dt.strftime("%A %x"),'start_time']).drop('date', axis=1)
    except Exception:
        schedule_df = pd.DataFrame()
    return render_template('home.html', data=schedule_df.to_html(classes=["table-bordered", "table-striped", "table-hover"]))

if __name__ == '__main__':
    app.run(host = "0.0.0.0", debug=True)

    