import requests
import datetime as dt
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
from functools import reduce
import json

# selenium packages
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

start = datetime.now()
print("SCRAPER STARTING AT: {}".format(start))


def birdland_scraper():
    r = requests.get("https://www.birdlandjazz.com/calendar/")
    soup = BeautifulSoup(r.text, "html.parser")
    results_days = soup.select('td[class*="has-event"]')

    records = []
    for result in results_days:
        result_len = len(result.contents)
        date = result.contents[0].text + " {}".format(datetime.now().year)
        for i in range(result_len)[1:]:
            name = result.contents[i].find("h1", {"class": "headliners summary"}).text
            time = result.contents[i].find("h3", {"class": "start-time"}).text
            records.append((date, time, name))

    df = pd.DataFrame(records, columns=["date", "time", "Birdland Jazz Club"])

    df["start_time"] = pd.to_datetime(df["time"]).datetime.strftime("%I:%M %p")
    df["date"] = pd.to_datetime(df["date"].apply(lambda x: x[3:]))
    df = df.set_index(["date", "start_time"]).drop("time", axis=1)

    return df


def bluenote_scraper():
    records = []
    for i in range(1, 4):
        r = requests.get(
            "https://www.ticketweb.com/venue/blue-note-jazz-club-new-york-ny/23798?REFID=tempsite&pl=bluenoteny&page={}".format(
                i
            )
        )
        soup = BeautifulSoup(r.text, "html.parser")
        main = soup.find("div", {"class": "section-body"})
        events = main.find_all("li", {"class": "media theme-mod"})
        year = dt.datetime.now().year
        month = dt.datetime.now().month

        for i in events:
            event = i.find("p", {"class": "event-name theme-title"}).find("a").text
            time_raw = i.find("p", {"class": "event-date theme-subTitle"}).text.strip()
            start_time = re.findall("(\d*:?\d+?\s*[AP]M)", time_raw)[0]

            date_raw = re.findall("(\w{3} \d{1,2})", time_raw)[0] + " " + str(year)
            dto = dt.datetime.strptime(date_raw, "%b %d %Y")

            if dto.month == 1 and month > 1:
                year += 1
                date_raw = re.findall("(\w{3} \d{1,2})", time_raw)[0] + " " + str(year)
                dto = dt.datetime.strptime(date_raw, "%b %d %Y")
                month = 1
            date = dto.strftime("%Y-%m-%d")

            records.append([date, start_time, event])

    df = pd.DataFrame(records, columns=["date", "start_time", "Blue Note"])

    df["start_time"] = pd.to_datetime(df["start_time"]).dt.strftime("%I:%M %p")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index(["date", "start_time"])
    return df


def cellar_dog_scraper():

    DRIVER_PATH = "/usr/bin/chromedriver"
    URL = "https://www.cellardog.net/music"

    months_list = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    # setup window and driver
    display = Display(visible=0, size=(1920, 1080))
    display.start()

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s, options=options)
    driver.get(URL)
    driver.set_window_size(1920, 1080)

    # scrape data
    calendar_data = driver.find_elements(By.XPATH, "//html")[0].text

    driver.quit()
    display.stop()

    # parse data and build df
    calendar_data_split = calendar_data.split("\n")
    records = []

    # get first day of data
    is_weekend = None
    for t in calendar_data_split:
        if 0 < len(t.strip()) <= 2 and t.strip().isdigit():
            day = int(t.strip())
        elif re.findall("(\d+:?\d*?[ap])", t.lower()):
            break

    # loop through data and create df
    for t in calendar_data_split:

        if "Friday & Saturday nights performances until 2AM" in t.strip():
            break

        if t.strip()[:-5] in months_list:
            year = t.strip()[-4:]
            month = t.strip()[:-5]

        elif re.findall("(\d+:?\d*?[ap])", t.lower()):
            event = t.strip("\n")

            start_time, artist = re.split("([0-9]{1,2}:?[0-9]{,2}?[ap]{1})", event)[-2:]
            start_time = f"{start_time[:-1]} {start_time[-1]}m".upper()
            if ":" not in start_time:
                start_time = re.sub("( [AP]M)", ":00 \\1", start_time)

            date_month = dt.datetime.strptime(month, "%B").month
            date = f"{year}-{date_month}-{day}"

            records.append([date, start_time, artist.strip()])

            dt_date = dt.datetime(int(year), int(date_month), int(day))
            if dt_date.weekday() in [4, 5]:
                is_weekend = 1
                if "11:30 PM" in start_time:
                    day += 1
            elif dt_date.weekday() == 6:
                day += 3
                is_weekend = 0
            else:
                day += 1

    df = pd.DataFrame(records, columns=["date", "start_time", "Fat Cat (Cellar Dog)"])
    df["date"] = pd.to_datetime(df["date"])
    df["start_time"] = pd.to_datetime(df["start_time"]).dt.strftime("%I:%M %p")
    df = df.set_index(["date", "start_time"])

    return df


def dizzys_scraper():
    r = requests.get("https://2021.jazz.org/dizzys-club")
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.select('a[href*="https://2021.jazz.org/"]')

    year = dt.datetime.now().year
    month = dt.datetime.now().month
    group_name = ""
    ds = ""

    records = []
    for artist in main[1:]:

        for date in artist.parent.parent.parent.find_all(
            "h4", {"data-preserve-html-node": "true"}
        ):
            if date != []:
                dates_tuples = re.findall("(\w{3} \d{1,2})(.{1}\d{1,2})?", date.text)
                dates_str = date.text

        for group in artist.parent.parent.parent.select(
            "h3", {"data-preserve-html-node": "true"}
        ):
            if group != []:
                group_name = group.text

        # create list of dates if we have range,i.e., contains '-'
        artist_days = []
        for date_tup in dates_tuples:
            month = date_tup[0][:4]
            date_range = date_tup[0] + date_tup[1]

            if "–" in date_range:
                days_L, days_H = re.findall("\d+", date_range)

                event_days = [
                    month + str(day) for day in range(int(days_L), int(days_H) + 1)
                ]
                artist_days.append(event_days)

            else:
                date_range = date_tup[0] + date_tup[1]
                artist_days.append([date_range])

        # split times where two dates present
        if len(dates_tuples) > 1:
            date_time_split = dates_str.split(dates_tuples[-1][0])
        else:
            date_time_split = [dates_str]

        event_times = []
        for time_str in date_time_split:
            event_times.append(re.findall("(\d+:?\d*[ap]m)", time_str))

        event_times_length = len(event_times)
        missing_time = 0
        for time in event_times:
            if time == []:
                missing_time = 1
        if missing_time:
            event_times = [time for i in range(event_times_length)]

        for i, day_group in enumerate(artist_days):
            for j, time_group in enumerate(event_times):
                if i == j:
                    for day in day_group:
                        for time in time_group:
                            date_raw = day + " " + str(year)
                            dto = dt.datetime.strptime(date_raw, "%b %d %Y")

                            if dto.month == 1 and month > 1:
                                year += 1
                                date_raw = date_raw + " " + str(year)
                                dto = dt.datetime.strptime(date_raw, "%b %d %Y")
                                month = 1

                            date = dto.strftime("%Y-%m-%d")
                            start_time = (
                                f"{time.strip()[:-2]} {time.strip()[-2]}m".upper()
                            )
                            if ":" not in start_time:
                                start_time = re.sub("( [AP]M)", ":00\\1", start_time)

                            records.append([date, start_time, group_name])

    df = pd.DataFrame(records, columns=["date", "start_time", "Dizzy's"])
    df["start_time"] = pd.to_datetime(df["start_time"]).dt.strftime("%I:%M %p")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index(["date", "start_time"])
    return df


def django_scraper():
    r = requests.get("https://www.thedjangonyc.com/events/")
    soup = BeautifulSoup(r.text, "html.parser")

    for s in soup:
        if soup.find("div"):
            results_days = soup.find_all("div", {"class": "grid__listings--group"})

    records = []
    for results_day in results_days:
        date_raw = results_day.get("data-date")
        dto = dt.datetime.strptime(date_raw, "%Y-%m-%d")
        date = dto.strftime("%Y-%m-%d")

        for event in results_day.find_all("article"):
            artist = event.find("h3", {"class": "event__title"}).text.strip("\n")
            date_time_raw = event.find("p", {"class": "event__info"}).text.strip("\n")

            times = re.findall("(\d*:?\d+?\s*[AP]M)", date_time_raw)
            if "-" in date_time_raw:
                times = [times[0]]

            for start_time in times:
                records.append([date, start_time, artist])

    df = pd.DataFrame(records, columns=["date", "time", "Django"])
    df["start_time"] = pd.to_datetime(df["time"], format="%I:%M%p").dt.strftime(
        "%I:%M %p"
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index(["date", "start_time"]).drop("time", axis=1)

    return df


def jazzgallery_scraper():
    r = requests.get("https://www.etix.com/ticket/v/3525/the-jazz-gallery")
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.find("div", {"id": "view", "class": "sixteen columns"})
    shows = main.find_all("div", {"class": "row performance show-divider"})
    records = []
    for show in shows:
        date = "{} {}".format(
            show.find("span", {"class": "month"}).text,
            show.find("span", {"class": "date"}).text,
        )
        time = show.find("div", {"class": "performance-datetime"}).text
        artist = show.find("h4", {"class": "performance-name"}).find("a").text
        records.append((date, time, artist))

    df = pd.DataFrame(records, columns=["date_temp", "time_temp", "Jazz Gallery"])
    df["start_time"] = pd.to_datetime(
        df["time_temp"].apply(lambda x: " ".join(x.split(" ", -1)[-2:]))
    ).datetime.strftime("%I:%M %p")
    df["date"] = pd.to_datetime(df["date_temp"] + " " + str(datetime.now().year))

    df = df.sort_values(["date", "start_time"])
    df = df.set_index(["date", "start_time"]).drop(["time_temp", "date_temp"], axis=1)

    return df


def kitano_scraper():
    r = requests.get(
        "https://www.instantseats.com/index.cfm?fuseaction=home.venue&VenueID=147"
    )
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.find("div", {"class": "event-list"})
    shows = main.find_all("div", {"class": "row"})
    records = []
    for show in shows:
        date = show.find("p", {"id": "event-date"}).text
        artist = show.find("h1", {"id": "event-title"}).text
        time = show.find("p", {"id": "event-time"}).text
        records.append((date, time, artist))
    records

    df = pd.DataFrame(records, columns=["date", "time", "Kitano"])
    df["date"] = pd.to_datetime(
        df["date"].apply(lambda x: x.replace(".", "/"))
        + "/"
        + "{}".format(datetime.now().year)
    )
    df["start_time"] = pd.to_datetime(df["time"]).datetime.strftime("%I:%M %p")
    df = df.set_index(["date", "start_time"]).drop(["time"], axis=1)

    return df


def mezzrow_scraper():
    r = requests.get("https://www.smallslive.com/events/calendar/")
    soup = BeautifulSoup(r.text, "html.parser")
    results_days = soup.select('div[class*="flex-column day-list"]')

    records = []
    for results_day in results_days:
        date_raw = results_day.find("div", {"class": "title1"}).get("data-date")
        dto = dt.datetime.strptime(date_raw, "%b. %d, %Y")
        date = dto.strftime("%Y-%m-%d")

        for event in results_day.find_all("div", {"class": "flex-column day-event"}):
            event_list = event.find_all("div")
            club = event_list[0].text.strip()
            start_times = re.findall("(\d*:?\d+?\s*[AP]M)", event_list[1].text.strip())
            artist = event_list[2].text.strip()

            for time in start_times:
                records.append([date, club, time, artist])

    df = pd.DataFrame(records, columns=["date", "club", "start_time", "Mezzrow"])
    df["date"] = pd.to_datetime(df["date"])
    df["start_time"] = pd.to_datetime(df["start_time"]).dt.strftime("%I:%M %p")
    df = df.loc[
        df["club"] == "Mezzrow",
    ].drop(columns=["club"])
    df = df.set_index(["date", "start_time"])

    return df


def smalls_scraper():
    r = requests.get("https://www.smallslive.com/events/calendar/")
    soup = BeautifulSoup(r.text, "html.parser")
    results_days = soup.select('div[class*="flex-column day-list"]')

    records = []
    for results_day in results_days:
        date_raw = results_day.find("div", {"class": "title1"}).get("data-date")
        dto = dt.datetime.strptime(date_raw, "%b. %d, %Y")
        date = dto.strftime("%Y-%m-%d")

        for event in results_day.find_all("div", {"class": "flex-column day-event"}):
            event_list = event.find_all("div")
            club = event_list[0].text.strip()
            start_times = re.findall("(\d*:?\d+?\s*[AP]M)", event_list[1].text.strip())
            artist = event_list[2].text.strip()

            for time in start_times:
                records.append([date, club, time, artist])

    df = pd.DataFrame(records, columns=["date", "club", "start_time", "Smalls"])
    df["date"] = pd.to_datetime(df["date"])
    df["start_time"] = pd.to_datetime(df["start_time"]).dt.strftime("%I:%M %p")
    df = df.loc[
        df["club"] == "Smalls",
    ].drop(columns=["club"])
    df = df.set_index(["date", "start_time"])

    return df


def smoke_scraper():
    r = requests.get("https://www.smokejazz.com/index.php/calendar/")
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.find("div", {"class": "calendar"})

    days = main.find_all("div", {"class": "cal_entries"})

    records = []
    for i in days:
        date = i.find("h5", {"class": "dateHead txt-drk"}).text
        for v in i.find_all("div", {"class": "event_entry tab-pane active"}):
            name = v.find("h3", {"class": "smkHead uppercase"}).text

            times_full_temp = [
                re.findall("(\d+:\d+\s.m)", p.text.lower()) for p in v.find_all("p")
            ]
            times_full = list(set([i for i in times_full_temp if i][0]))

            obs = len(times_full)
            dates_full = [date for i in range(obs)]
            names_full = [name for i in range(obs)]
            records.append(list(zip(dates_full, times_full, names_full)))

    records2 = []
    for i in records:
        for j in i:
            records2.append(j)

    df = pd.DataFrame(records2, columns=["date", "time", "Smoke Bar"])
    df["start_time"] = pd.to_datetime(df["time"]).datetime.strftime("%I:%M %p")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index(["date", "start_time"]).drop("time", axis=1)

    return df


def villagevanguard_scraper():
    r = requests.get(
        "https://www.squadup.com/api/v3/events?user_ids=4158761&page_size=200&additional_attr=sold_out&include=custom_fields"
    )
    data = json.loads(r.text)

    shows = [i["name"].split("-", 1)[1].strip("\n") for i in data["events"]]
    date = [i["start_at"].split("T", 1)[0] for i in data["events"]]
    time = [i["start_at"].split("T", 1)[1].split("-", 1)[0] for i in data["events"]]
    records = list(zip(date, time, shows))

    df = pd.DataFrame(records, columns=["date", "time", "Village Vanguard"])
    df["date"] = pd.to_datetime(df["date"])
    df["start_time"] = pd.to_datetime(df["time"]).dt.strftime("%I:%M %p")

    df = df.set_index(["date", "start_time"]).drop(["time"], axis=1)
    return df


def zinc_scraper():
    r = requests.get("https://zincjazz.com/shows/")
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.find_all("div", {"class": "edgtf-row-grid-section-wrapper"})[1]

    days = main.find_all("a", {"class": "edgtf-el-item-link-outer"})

    records = []
    for i in days:
        r = requests.get(i["href"])
        soup = BeautifulSoup(r.text, "html.parser")
        date = soup.find("span", {"class": "offbeat-event-info-item-desc"}).text
        name = soup.find(["h2", "h4"]).text

        times_temp = [
            re.findall("(\d*:?\d+?\s*[ap]m)", i.text.lower())
            for i in soup.find_all(["p", "h4"])
        ]

        times_full_temp = [val for sublist in times_temp for val in sublist]
        times_full = list(set(times_full_temp))
        obs = len(times_full)

        dates_full = [date for i in range(obs)]
        names_full = [name for i in range(obs)]
        records.append(list(zip(dates_full, times_full, names_full)))
    records2 = []
    for i in records:
        for j in i:
            records2.append(j)

    df = pd.DataFrame(records2, columns=["date", "time", "Zinc Bar"])
    df["start_time"] = pd.to_datetime(
        df["time"].apply(
            lambda x: (re.findall("\d+", x)[0] + ":00" + x[-2:]).replace(" ", "")
            if ":" not in x
            else x.replace(" ", "")
        )
    ).datetime.strftime("%I:%M %p")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index(["date", "start_time"]).drop("time", axis=1)

    return df


"""
Create datasets
"""
scrapers = [
    birdland_scraper,
    bluenote_scraper,
    cellar_dog_scraper,
    dizzys_scraper,
    django_scraper,
    kitano_scraper,
    mezzrow_scraper,
    smalls_scraper,
    smoke_scraper,
    villagevanguard_scraper,
]
data_frames = {}

for scraper in scrapers:
    try:
        data_frames[f"{scraper.__name__}"] = scraper()
    except:
        # print(e)
        print("{} CRASHED!".format(scraper).upper())

for k, v in data_frames.copy().items():
    if len(v) == 0:
        data_frames.pop(k)

full_df = reduce(
    lambda left, right: pd.merge(left, right, on=["date", "start_time"], how="outer"),
    [*data_frames.values()],
).sort_values(["date", "start_time"])
final_df = full_df.loc[datetime.today() - timedelta(days=1) :]

# filter NaNs
final_df = final_df.astype("object").fillna(" ")

SAVE_PATH = ""
# added utf-8 encoding to fix write error on ubuntu
final_df.to_csv("{}schedule.csv".format(SAVE_PATH), encoding="utf-8")
final_df.to_html("{}schedule.html".format(SAVE_PATH))

finish = datetime.now()
print("SCRAPER FINISHED AT: {}".format(finish))
print("TIME ELAPSED: {}".format(finish - start))
